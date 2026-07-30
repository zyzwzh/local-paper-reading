# local-paper-reading

本地论文智能阅读 Skill — 自动搜索 arXiv 论文 + 逐段中文标注，大一新生也能读懂英文文献。

## 这是什么

输入一个主题关键词（如"Transformer"），Skill 自动完成"搜索论文 → 筛选入门友好型 → 下载 PDF → 逐段标注中文翻译/术语/讲解/高亮 → 输出 Word 文件"全流程。也可直接标注本地 PDF/Word/TXT 论文。基于 OpenVINO INT8 量化加速，本地推理零隐私泄露。

---

## 核心功能

### 新增：自动搜索论文（面向零基础新生）

```
用户："我想了解 GAN"
      ↓
自动搜索 arXiv → 筛选入门友好型 → 下载 PDF → 逐段标注 → 输出 Word
```

搜索筛选策略：
- 标题含 survey/tutorial/introduction 优先（综述教程最适合入门）
- 高引用优先（经典奠基论文）
- 短论文优先（阅读负担小）
- 每篇论文附带"入选理由"

### 标注效果

每段原文后自动生成四层标注：

| 层级 | 颜色 | 内容 |
|------|------|------|
| 翻译 | 蓝色斜体 | 整段中文翻译 |
| 术语 | 绿色 | 英文术语 + 中文 + 一句话解释 |
| 讲解 | 灰色底色 | 背景补充、公式说明、直觉理解 |
| 重点句 | 黄色高亮 | 核心贡献句、关键结果句 |

---

## 目录结构（符合 OpenVINO 官方 local-ai-skill-authoring 标准）

```
local-paper-reading/
├── SKILL.md            # 路由规范（双语触发词 + run.ps1 接口）
├── info.json           # 运行时配置（venv/内存/模型列表）
├── meta.json           # 商店元数据（显示名/图标/用例）
├── requirements.txt    # Python 依赖
├── scripts/
│   ├── run.ps1         # 固定入口（硬件检测 → 环境安装 → 启动客户端）
│   ├── install-env.ps1 # venv 管理 + 依赖安装
│   ├── client.py       # 短命客户端（命名管道通信）
│   ├── server.py       # 长命服务器（OpenVINO 模型常驻）
│   └── paper_engine.py # 论文搜索 + 文档解析 + 逐段标注引擎
└── tests/
    └── test.ps1        # 端到端测试
```

---

## 使用方式

### 搜索 + 标注（一句话搞定）

```powershell
scripts\run.ps1 "我想了解 Transformer"
```

自动搜索 arXiv，筛选最适合入门的论文，下载并逐段标注。

### 只搜索不标注

```powershell
scripts\run.ps1 "search deep learning" --search-only
```

### 标注本地文件

```powershell
scripts\run.ps1 "C:\papers\attention.pdf"
scripts\run.ps1 "C:\papers\attention.pdf" --depth intensive  # 精读
scripts\run.ps1 "C:\papers\attention.pdf" --depth skimming   # 泛读
scripts\run.ps1 "C:\papers\attention.pdf" --depth overview    # 速览
```

### 续传模型下载

```powershell
scripts\run.ps1 --continue
```

---

## 架构

### Client-Server 架构（官方标准推荐）

```
┌──────────┐ Named Pipe       ┌──────────────┐
│ client.py│ ──────────────► │  server.py   │
│ (短命)   │ \\.\pipe\...     │  (长命)      │
└──────────┘                  │  模型常驻     │
                              └──────────────┘
```

- 模型加载一次（冷启动 10-60s），后续调用连接常驻服务器（1-3s）
- 服务器状态机：starting → downloading → loading → running
- 命名管道协议：status / request / shutdown

### OpenVINO 异构加速

```
[CPU] 翻译模型 (INT8 量化)
[GPU] 术语识别模型 (INT8 量化)
[NPU] 关键句提取模型 (INT8 量化)

GPU 优先 → NPU 次之 → CPU 兜底
```

| 指标 | CPU (无优化) | GPU (OpenVINO INT8) | 加速比 |
|------|-------------|---------------------|--------|
| 模型大小 | 153 MB | 38.4 MB | 3.98x 压缩 |
| 推理延迟 | 65.75 ms | 20.74 ms | 3.17x 加速 |

### Hybrid AI

| 任务 | 执行位置 | 原因 |
|------|----------|------|
| 论文搜索 | 云端 API | arXiv API 需要联网 |
| 筛选决策 | 云端大模型 | 需要语义理解 |
| 段落翻译 | 本地模型 | 批量大、可量化 |
| 术语识别 | 本地模型 | 模式匹配 |
| 关键句提取 | 本地模型 | 分类任务 |
| 背景讲解 | 云端大模型 | 需要知识储备 |

---

## 退出码

| 码 | 含义 |
|----|------|
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 连接错误 |
| 3 | 模型下载中（需 --continue） |

---

## 运行测试

```powershell
.\tests\test.ps1
```

测试覆盖：无参数帮助、arXiv 搜索、本地文件标注、搜索+标注全流程、错误路径处理。
