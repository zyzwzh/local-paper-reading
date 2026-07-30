"""
server.py — 长命服务器，OpenVINO 模型常驻 + 论文搜索/标注服务

状态机：starting → downloading → loading → running
                                    ↓ (异常)
                                   error

命名管道协议：
  请求: {"op": "status"} / {"op": "request", ...} / {"op": "shutdown", "timeout": N}
  响应: {"ok": true, ...} / {"ok": false, "error": "..."}
"""
import sys
import os
import time
import json
import traceback
import threading
from multiprocessing.connection import Listener

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

# 日志目录（权限不足时回退到 AppData\Local\Temp）
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
    LOG_DIR = os.path.dirname(os.path.abspath(__file__))


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [server pid={os.getpid()}] {msg}", flush=True)


# ============================================================
# OpenVINO 推理引擎
# ============================================================

class InferenceEngine:
    """
    OpenVINO 推理引擎，负责本地模型推理。
    状态：starting → downloading → loading → running / error
    """

    def __init__(self):
        self.state = "starting"
        self.core = None
        self.compiled_model = None
        self.device = "CPU"
        self.error_msg = ""

    def initialize(self):
        """初始化：加载 OpenVINO 模型"""
        self.state = "downloading"
        log("Checking model files...")

        model_dir = self._get_model_dir()
        required = ["openvino_model.xml", "openvino_model.bin"]

        # 检查模型文件是否存在
        if not all(os.path.exists(os.path.join(model_dir, f)) for f in required):
            log("Model not downloaded yet, using demo mode (no OpenVINO model)")
            self.state = "running"
            self.compiled_model = None  # 演示模式
            return

        self.state = "loading"
        log("Loading OpenVINO model...")

        try:
            from openvino import Core
            self.core = Core()
            devices = self.core.available_devices
            log(f"Available devices: {devices}")

            # GPU 优先 → NPU 次之 → CPU 兜底
            model_path = os.path.join(model_dir, "openvino_model.xml")
            for dev in devices:
                if dev.startswith("GPU"):
                    self.device = dev
                    break
                elif dev.startswith("NPU"):
                    self.device = dev

            self.compiled_model = self.core.compile_model(model_path, self.device)
            log(f"Model loaded on {self.device}")
            self.state = "running"

        except Exception as e:
            self.state = "error"
            self.error_msg = str(e)
            log(f"Model load failed: {e}")
            log("Falling back to demo mode (no inference)")
            self.state = "running"
            self.compiled_model = None

    def _get_model_dir(self):
        """获取模型目录"""
        return os.path.join(os.path.expanduser("~"), ".openvino", "models", "nano-translation-int8")

    def infer(self, text, task_type="translate"):
        """
        推理接口。

        Args:
            text: 输入文本
            task_type: translate / terms / explain / highlight

        Returns:
            推理结果（字符串或列表）
        """
        if self.compiled_model is None:
            # 演示模式：返回模拟数据
            return self._demo_infer(text, task_type)

        # 真实推理（需要模型输入输出适配）
        try:
            # TODO: 根据实际模型的输入输出格式适配
            # 这里是接口预留，实际使用时需要根据模型调整
            result = self._run_model(text, task_type)
            return result
        except Exception as e:
            log(f"Inference error ({task_type}): {e}")
            return self._demo_infer(text, task_type)

    def _run_model(self, text, task_type):
        """真实模型推理（预留接口）"""
        # 实际使用时需要：
        # 1. 对文本进行 tokenize
        # 2. 调用 compiled_model 推理
        # 3. 解码输出
        # 这里返回模拟数据作为占位
        return self._demo_infer(text, task_type)

    def _demo_infer(self, text, task_type):
        """演示模式推理（无模型时的模拟输出）"""
        if task_type == "translate":
            return f"[本地翻译] {text[:80]}..."
        elif task_type == "terms":
            return [{"en": "NLP", "zh": "自然语言处理", "explain": "让计算机理解人类语言"}]
        elif task_type == "explain":
            return "[本地讲解] 本段讨论了相关技术的核心概念。"
        elif task_type == "highlight":
            return [text[:40]] if len(text) > 40 else [text]
        elif task_type == "glossary":
            # 批量术语翻译：返回 JSON 列表
            import json as _json
            terms = [t.strip() for t in text.strip().split("\n") if t.strip()]
            return [
                {"en": t, "zh": f"[术语]{t}", "explain": "演示模式"}
                for t in terms[:20]
            ]
        elif task_type == "paper_summary":
            return "[论文摘要] 本论文提出了一种新方法，在相关任务上取得了显著效果。（演示模式）"
        elif task_type == "batch_translate":
            # 批量翻译：按 [段落N] 分割返回
            import re as _re
            parts = _re.split(r'\[段落\d+\]', text)
            parts = [p.strip() for p in parts if p.strip()]
            if not parts:
                return text[:200]
            return "\n\n".join(
                f"[段落{i+1}]\n[批量翻译] {p[:60]}..."
                for i, p in enumerate(parts)
            )
        return ""

    def get_status(self):
        return {
            "state": self.state,
            "device": self.device,
            "model_loaded": self.compiled_model is not None,
            "error": self.error_msg if self.state == "error" else "",
        }


# ============================================================
# 请求处理器
# ============================================================

def handle_request(engine, req):
    """处理客户端请求"""
    op = req.get("op", "")

    if op == "status":
        status = engine.get_status()
        status["ok"] = True
        status["pid"] = os.getpid()
        status["uptime_s"] = int(time.time() - START_TIME)
        return status

    elif op == "request":
        action = req.get("action", "")

        if action == "search":
            # 搜索论文
            query = req.get("query", "")
            log(f"Search request: {query}")

            from paper_engine import search_papers
            papers = search_papers(query, max_results=req.get("max_results", 10))

            # 返回前 5 篇
            top_papers = []
            for p in papers[:5]:
                top_papers.append({
                    "标题": p["title"],
                    "作者": p["authors"],
                    "arXiv ID": p["arxiv_id"],
                    "发表日期": p["published"],
                    "入选理由": p["entry_reason"],
                    "入门友好度": p["beginner_score"],
                })

            return {"ok": True, "结果数": len(top_papers), "论文列表": top_papers}

        elif action == "annotate":
            # 标注论文
            from paper_engine import search_and_annotate, annotate_file

            depth = req.get("depth", "intensive")
            output_dir = req.get("output_dir")

            # 推理回调
            def infer_callback(text, task_type):
                return engine.infer(text, task_type)

            if "query" in req:
                # 搜索 + 标注
                result = search_and_annotate(
                    req["query"], output_dir, depth, infer_callback
                )
            elif "file_path" in req:
                # 直接标注本地文件
                result = annotate_file(
                    req["file_path"], output_dir, depth, infer_callback
                )
            else:
                return {"ok": False, "error": "需要提供 query 或 file_path"}

            return result

        else:
            return {"ok": False, "error": f"未知操作: {action}"}

    elif op == "shutdown":
        log("Shutdown requested")
        return {"ok": True, "state": "shutting_down"}

    else:
        return {"ok": False, "error": f"未知 op: {op}"}


# ============================================================
# 主循环
# ============================================================

START_TIME = time.time()
engine = InferenceEngine()


def main():
    log(f"Starting server on {PIPE_ADDRESS}")

    # 后台线程初始化引擎
    init_thread = threading.Thread(target=engine.initialize, daemon=True)
    init_thread.start()

    listener = Listener(PIPE_ADDRESS, authkey=AUTHKEY)

    while True:
        try:
            conn = listener.accept()
            try:
                req = conn.recv()
                log(f"Request: {req.get('op', '?')}")

                resp = handle_request(engine, req)
                conn.send(resp)

                if req.get("op") == "shutdown":
                    log("Shutting down...")
                    break

            except Exception as e:
                log(f"Request error: {e}")
                try:
                    conn.send({"ok": False, "error": str(e)})
                except:
                    pass
            finally:
                conn.close()

        except Exception as e:
            log(f"Accept error: {e}")
            time.sleep(1)

    listener.close()
    log("Server stopped.")


if __name__ == "__main__":
    main()
