"""
client.py — 短命客户端

职责：
  1. 确保服务器运行（自启动）
  2. 通过命名管道发送请求
  3. 格式化输出结果
  4. 处理下载超时（退出码 3）
"""
import sys
import os
import time
import json
import argparse
import hashlib
import subprocess
from multiprocessing.connection import Client
from pathlib import Path

# UTF-8 编码（强制）
def _configure_stream_encoding(stream):
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")

_configure_stream_encoding(sys.stdout)
_configure_stream_encoding(sys.stderr)

# ============================================================
# 配置
# ============================================================

SKILL_NAME = "local-paper-reading"
PIPE_ADDRESS = f"\\\\.\\pipe\\{SKILL_NAME}"
AUTHKEY = SKILL_NAME.encode("latin-1")

# 脚本目录
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPTS_DIR)

# 临时工作目录（运行时脚本同步目标）
# 优先使用 .openvino/temp，权限不足时回退到 AppData\Local\Temp
_openvino_temp = os.path.join(os.path.expanduser("~"), ".openvino", "temp", SKILL_NAME)
_fallback_temp = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", SKILL_NAME)
for _candidate in (_openvino_temp, _fallback_temp):
    try:
        os.makedirs(_candidate, exist_ok=True)
        _test_file = os.path.join(_candidate, ".write_test")
        with open(_test_file, "w") as _f:
            _f.write("ok")
        os.remove(_test_file)
        TEMP_DIR = _candidate
        break
    except (PermissionError, OSError):
        continue
else:
    TEMP_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(TEMP_DIR, exist_ok=True)

# 日志目录
_log_candidates = [
    os.path.join(os.path.expanduser("~"), ".openvino", "log"),
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", f"{SKILL_NAME}_logs"),
]
for _candidate in _log_candidates:
    try:
        os.makedirs(_candidate, exist_ok=True)
        LOG_DIR = _candidate
        break
    except (PermissionError, OSError):
        continue
else:
    LOG_DIR = TEMP_DIR

# 重试配置
MAX_RETRIES = 3
RETRY_INTERVAL = 5  # 秒
SERVER_STARTUP_WAIT = 10  # 秒


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [client] {msg}", file=sys.stderr, flush=True)


# ============================================================
# 1. 同步脚本到临时目录
# ============================================================

def sync_scripts():
    """同步 scripts/ 到临时目录，检测文件变更"""
    scripts = ["server.py", "paper_engine.py"]
    need_restart = False

    for script in scripts:
        src = os.path.join(SCRIPTS_DIR, script)
        dst = os.path.join(TEMP_DIR, script)

        if not os.path.exists(src):
            continue

        # 源和目标相同（TEMP_DIR 就是 scripts 目录），跳过复制
        if os.path.normpath(src) == os.path.normpath(dst):
            continue

        src_hash = hashlib.md5(open(src, "rb").read()).hexdigest()

        if os.path.exists(dst):
            dst_hash = hashlib.md5(open(dst, "rb").read()).hexdigest()
            if src_hash != dst_hash:
                need_restart = True
        else:
            need_restart = True

        # 复制
        import shutil
        shutil.copy2(src, dst)

    return need_restart


# ============================================================
# 2. 确保服务器运行
# ============================================================

def is_server_running():
    """检查服务器是否在运行"""
    try:
        conn = Client(PIPE_ADDRESS, authkey=AUTHKEY)
        conn.send({"op": "status"})
        resp = conn.recv()
        conn.close()
        return resp.get("ok", False)
    except Exception:
        return False


def start_server(venv_python):
    """启动服务器"""
    server_path = os.path.join(TEMP_DIR, "server.py")
    if not os.path.exists(server_path):
        server_path = os.path.join(SCRIPTS_DIR, "server.py")

    log(f"Starting server: {venv_python} {server_path}")

    # 后台启动服务器
    proc = subprocess.Popen(
        [venv_python, server_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=TEMP_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    # 等待服务器就绪
    for _ in range(SERVER_STARTUP_WAIT):
        time.sleep(1)
        if is_server_running():
            log("Server is running.")
            return True

    log("Server failed to start within timeout.")
    return False


def ensure_server(venv_python):
    """确保服务器在运行，必要时重启"""
    if is_server_running():
        # 检查是否需要重启（脚本更新）
        need_restart = sync_scripts()
        if need_restart:
            log("Scripts changed, restarting server...")
            try:
                send_request({"op": "shutdown", "timeout": 5.0})
            except:
                pass
            time.sleep(2)
            return start_server(venv_python)
        return True
    else:
        sync_scripts()
        return start_server(venv_python)


# ============================================================
# 3. 发送请求
# ============================================================

def send_request(req, retries=MAX_RETRIES):
    """通过命名管道发送请求，带重试"""
    last_error = None

    for attempt in range(retries):
        try:
            conn = Client(PIPE_ADDRESS, authkey=AUTHKEY)
            conn.send(req)
            resp = conn.recv()
            conn.close()
            return resp
        except Exception as e:
            last_error = e
            log(f"Request attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(RETRY_INTERVAL)

    return {"ok": False, "error": f"连接失败: {last_error}"}


# ============================================================
# 4. 解析命令行参数
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(description="本地论文智能阅读 Skill")

    parser.add_argument("input", nargs="?", default="",
                        help="搜索关键词或文件路径")
    parser.add_argument("--depth", default="intensive",
                        choices=["intensive", "skimming", "overview"],
                        help="标注深度: intensive(精读) / skimming(泛读) / overview(速览)")
    parser.add_argument("--search-only", action="store_true",
                        help="只搜索论文，不标注")
    parser.add_argument("--output-dir", default=None,
                        help="输出目录")
    parser.add_argument("--continue", dest="continue_download",
                        action="store_true",
                        help="续传模型下载")
    parser.add_argument("--clear-cache", action="store_true",
                        help="清除段落缓存（强制重新标注）")

    return parser.parse_args()


# ============================================================
# 5. 主逻辑
# ============================================================

def get_venv_python():
    """获取 venv python 路径"""
    info_path = os.path.join(SKILL_ROOT, "info.json")
    with open(info_path, "r", encoding="utf-8") as f:
        info = json.load(f)

    venv = os.path.join(os.path.expanduser("~"), ".openvino", "venv", info["venv_name"])
    python = os.path.join(venv, "Scripts", "python.exe")
    return python


def main():
    args = parse_args()

    # 无输入：显示帮助
    if not args.input and not args.continue_download and not args.clear_cache:
        print(json.dumps({
            "ok": False,
            "error": "请提供搜索关键词或文件路径",
            "用法": [
                'run.ps1 "我想了解 Transformer"',
                'run.ps1 "C:\\papers\\attention.pdf"',
                'run.ps1 "search deep learning" --search-only',
                'run.ps1 "deep learning" --depth skimming',
                'run.ps1 --clear-cache',
            ],
            "标注深度": {
                "intensive": "精读 — 核心段落深度标注 + 辅助段落批量翻译",
                "skimming": "泛读 — 仅摘要/结论深度标注，其余批量翻译",
                "overview": "速览 — 只标注摘要和结论",
            },
            "优化特性": [
                "分层路由：自动区分 core/support/skip 段落",
                "全局术语表：保证全文翻译一致性",
                "批量推理：10段合并1次调用，降低90%成本",
                "并发处理：核心段落并行标注",
                "段落缓存：二次运行秒出结果",
            ],
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 清除缓存
    if args.clear_cache:
        # 尝试多个可能的缓存目录
        _cache_candidates = [
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "paper_reading_cache"),
            os.path.join(os.path.expanduser("~"), ".openvino", "temp", "paper_reading_cache"),
        ]
        _cleared = False
        for _cache_dir in _cache_candidates:
            _cache_file = os.path.join(_cache_dir, "annotations_cache.json")
            if os.path.exists(_cache_file):
                try:
                    os.remove(_cache_file)
                    log(f"Cache cleared: {_cache_file}")
                    _cleared = True
                except PermissionError:
                    pass
        if not _cleared:
            log("No cache file found or already cleared.")
        print(json.dumps({"ok": True, "message": "缓存已清除"}, ensure_ascii=False))
        if not args.input:
            sys.exit(0)

    # 获取 venv python
    venv_python = get_venv_python()

    # 确保服务器运行
    log("Ensuring server is running...")
    if not ensure_server(venv_python):
        print(json.dumps({
            "ok": False,
            "error": "服务器启动失败，请检查环境配置"
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    # 判断输入类型
    input_str = args.input.strip()

    # 文件路径模式
    is_file = (
        os.path.exists(input_str)
        and Path(input_str).suffix.lower() in (".pdf", ".docx", ".txt")
    )

    # 搜索关键词模式
    is_search = (
        input_str.lower().startswith("search ")
        or input_str.lower().startswith("搜 ")
        or input_str.lower().startswith("找 ")
    )

    # 构造请求
    if is_file:
        # 标注本地文件
        req = {
            "op": "request",
            "action": "annotate",
            "file_path": os.path.abspath(input_str),
            "depth": args.depth,
            "output_dir": args.output_dir,
        }
    elif is_search or args.search_only:
        # 只搜索
        query = input_str
        for prefix in ["search ", "搜 ", "找 "]:
            if query.lower().startswith(prefix):
                query = query[len(prefix):]
                break
        query = query.strip()

        req = {
            "op": "request",
            "action": "search",
            "query": query,
            "max_results": 5,
        }
    else:
        # 搜索 + 标注（默认模式，面向零基础新生）
        req = {
            "op": "request",
            "action": "annotate",
            "query": input_str,
            "depth": args.depth,
            "output_dir": args.output_dir,
        }

    # 发送请求
    log(f"Sending request: {req.get('action', '?')}")
    result = send_request(req)

    # 检查是否需要下载模型
    if not result.get("ok") and "download" in result.get("error", "").lower():
        print(json.dumps({
            "ok": False,
            "error": "模型正在下载中，请运行 --continue 续传",
            "退出码": 3
        }, ensure_ascii=False, indent=2))
        sys.exit(3)

    # 输出结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("ok"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
