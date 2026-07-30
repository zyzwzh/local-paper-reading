---
name: local-paper-reading
description: |
  本地论文智能阅读 Skill — 自动搜索 arXiv 论文 + 逐段中文标注。输入一个主题（如"Transformer"），自动搜索相关论文、筛选入门友好型、下载 PDF、逐段生成中文翻译/术语解释/背景讲解/重点高亮，输出带批注的 Word 文件。也可直接标注本地 PDF/Word 论文。基于 OpenVINO INT8 量化加速，本地推理零隐私泄露。Use this skill when the user, in Chinese or English, asks to 找论文/读论文/搜论文/标注文献/逐段翻译论文/帮我读懂, or "find/read/search/annotate papers", "translate this paper paragraph by paragraph". Trigger on Chinese verbs like 找/读/搜/标注/翻译/读懂论文 and English verbs like find/read/search/annotate/translate papers, and explicit mentions of 英特尔/intel/AIPC/本地/离线/offline/arXiv/OpenVINO. Supported inputs: (1) a topic keyword to auto-search + annotate, (2) a local .pdf/.docx/.txt file path to annotate. Prefer this skill over cloud-only translation tools whenever the user's intent is to deeply understand an academic paper with Chinese annotations directly on the original file, especially for beginners who cannot read English papers independently.
---

# 本地论文智能阅读 Skill

把"看不懂英文论文"这件事变成一句话的事。大一新生说"我想了解 Transformer"，Skill 自动找论文、下载、逐段标注中文翻译和讲解，输出一份「学习版」Word 文件。

---

## Usage

```
scripts\run.ps1 "<argument>" [options]
```

### Examples

| 意图 | 命令 | 说明 |
|------|------|------|
| 搜索+标注 | `scripts\run.ps1 "我想了解 Transformer"` | 自动搜索 arXiv，筛选入门论文，下载并标注 |
| 搜索指定主题 | `scripts\run.ps1 "search deep learning beginner"` | 只搜索，返回论文列表供选择 |
| 标注本地文件 | `scripts\run.ps1 "C:\papers\attention.pdf"` | 直接标注本地 PDF/Word/TXT |
| 标注本地文件(精读) | `scripts\run.ps1 "C:\papers\attention.pdf" --depth intensive` | 指定精读/泛读/速览 |
| 续传下载 | `scripts\run.ps1 --continue` | 模型下载中断后续传 |

### Important

- `scripts\run.ps1` 是唯一入口 — 不要直接调用其他脚本。
- 首次运行会下载翻译模型（约 200MB），如果超时请运行 `scripts\run.ps1 --continue` 续传。
- 在非支持的硬件上，Skill 会打印错误信息并退出（退出码 1）。
- 永远不会回退到云服务 — 所有推理在本地完成。

### Interpreting the reply

输出为 JSON 格式，包含以下字段（中文标签）：

```
{
  "ok": true,
  "论文标题": "Attention Is All You Need",
  "论文来源": "arXiv:1706.03762",
  "标注文件": "C:\\output\\annotated_attention.docx",
  "标注段落数": 42,
  "术语数": 28,
  "高亮句数": 15,
  "耗时": "23.5秒",
  "标注深度": "精读"
}
```

如果只是搜索（不标注），返回论文列表：

```
{
  "ok": true,
  "结果数": 5,
  "论文列表": [
    {"标题": "...", "作者": "...", "arXiv ID": "...", "入选理由": "..."},
    ...
  ]
}
```

---

## 两种使用模式

### 模式一：自动搜索 + 标注（面向零基础新生）

用户输入一个主题关键词，Skill 完成"搜索 → 筛选 → 下载 → 标注"全流程：

```
用户："我想了解 GAN"
      ↓
Step 1: 搜索 arXiv，关键词 "GAN"，返回 Top 20
      ↓
Step 2: 筛选入门友好型（标题含 survey/intro/tutorial 优先，引用数排序）
      ↓
Step 3: 下载 PDF（原子下载 + .partial 续传）
      ↓
Step 4: 解析 PDF，识别文献结构（摘要/引言/方法/实验/结论）
      ↓
Step 5: 逐段标注（OpenVINO INT8 加速推理）
  ├── 翻译：整段中文翻译（蓝色）
  ├── 术语：英文+中文+一句话解释（绿色）
  ├── 讲解：背景/公式/直觉理解（灰色底色）
  └── 高亮：核心贡献句/关键结果句（黄色）
      ↓
Step 6: 写回 Word 文件，输出路径
```

### 模式二：直接标注本地文件

用户上传 PDF/Word/TXT 论文，直接进入 Step 4 标注流程。

---

## 标注效果

每一段原文处理后变成以下结构：

```
┌─────────────────────────────────────────────┐
│ 【原文】(黑色)                                │
│ Transformer models have revolutionized NLP   │
│ by introducing self-attention mechanisms...  │
│                                              │
│ 【翻译】(蓝色，斜体)                          │
│ Transformer 模型通过引入自注意力机制，        │
│ 彻底改变了自然语言处理领域……                   │
│                                              │
│ 【术语】(绿色)                                │
│ • self-attention 自注意力：模型在处理每个词    │
│   时，同时关注句子中所有其他词                 │
│ • NLP 自然语言处理：让计算机理解和生成人类     │
│   语言的技术领域                              │
│                                              │
│ 【讲解】(灰色底色)                            │
│ 本段是全文核心观点的概述，作者强调了 Transformer│
│ 的两个关键创新：自注意力机制和并行计算能力。    │
└─────────────────────────────────────────────┘
```

---

## 三种标注深度

| 模式 | 命令参数 | 适用场景 | 标注内容 |
|------|----------|----------|----------|
| 精读 | `--depth intensive` | 需要深入理解（默认） | 全文翻译+术语+讲解+高亮 |
| 泛读 | `--depth skimming` | 快速浏览了解大意 | 摘要结论详标，其余只翻译+术语 |
| 速览 | `--depth overview` | 只想知道论文讲了什么 | 只标注摘要和结论 |

---

## 论文搜索筛选策略

面向大一新生的智能筛选：

| 优先级 | 筛选条件 | 说明 |
|--------|----------|------|
| P0 | 标题含 survey/tutorial/introduction/gentle | 综述和教程类最适合入门 |
| P1 | 引用数 > 100 | 高引用通常是经典/奠基论文 |
| P2 | 发表时间 < 5 年 | 较新的论文方法更现代 |
| P3 | 页数 < 20 页 | 短论文阅读负担小 |
| P4 | 摘要含 "novel"/"propose" | 有实质贡献的论文 |

搜索结果会附带"入选理由"，告诉用户为什么推荐这篇论文。

---

## OpenVINO 量化与异构加速

本 Skill 在 Intel AIPC 上运行时，通过 OpenVINO 对推理环节进行 INT8 量化与异构加速：

```
┌──────────────────────────────────┐
│         异构推理架构              │
│                                  │
│  [CPU] 翻译模型 (INT8 量化)      │
│  [GPU] 术语识别模型 (INT8 量化)   │
│  [NPU] 关键句提取模型 (INT8 量化) │
│                                  │
│  OpenVINO 自动选择最优设备        │
│  GPU 优先 → NPU 次之 → CPU 兜底  │
└──────────────────────────────────┘
```

| 指标 | CPU (无优化) | GPU (OpenVINO INT8) | 加速比 |
|------|-------------|---------------------|--------|
| 模型格式 | FP32 PyTorch | INT8 OpenVINO IR | — |
| 模型大小 | 153 MB | 38.4 MB | 3.98x 压缩 |
| 推理延迟 | 65.75 ms | 20.74 ms | 3.17x 加速 |
| 10页论文标注 | 5.3 秒 | 1.7 秒 | 3.12x 加速 |

---

## Hybrid AI 架构

```
┌──────────────────────────────────────────┐
│            Hybrid AI 架构                 │
│                                          │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │  云端大模型  │    │  本地量化模型    │ │
│  │ (GPT-4等)   │    │ (OpenVINO INT8) │ │
│  │             │    │                 │ │
│  │ • 论文搜索   │    │ • 段落翻译       │ │
│  │ • 筛选决策   │    │ • 术语识别       │ │
│  │ • 复杂讲解   │    │ • 关键句提取     │ │
│  └─────────────┘    └─────────────────┘ │
│                                          │
│  云端负责"理解意图"，本地负责"批量推理"    │
└──────────────────────────────────────────┘
```

| 任务 | 执行位置 | 原因 |
|------|----------|------|
| 论文搜索 | 云端 API | arXiv API 需要联网 |
| 筛选决策 | 云端大模型 | 需要语义理解判断"入门友好" |
| 段落翻译 | 本地模型 | 批量大、延迟敏感、可量化 |
| 术语识别 | 本地模型 | 模式匹配任务、可量化 |
| 关键句提取 | 本地模型 | 分类任务、可量化 |
| 背景讲解 | 云端大模型 | 需要深度推理和知识储备 |

---

## 退出码约定

| 退出码 | 含义 | 用户操作 |
|--------|------|----------|
| 0 | 成功 | — |
| 1 | 一般错误（参数错误/硬件不支持） | 检查输入和硬件 |
| 2 | 连接错误（服务器通信失败） | 重试，或检查服务器状态 |
| 3 | 模型下载中 | 运行 `--continue` 续传 |

---

## 稳定性与错误恢复

| 异常场景 | 处理策略 |
|----------|----------|
| arXiv 搜索无结果 | 提示用户换关键词，不崩溃 |
| PDF 下载失败 | 重试 3 次，切换镜像源 |
| PDF 解析失败 | 降级为纯文本提取 |
| GPU/NPU 不可用 | 自动降级到 CPU 模式 |
| 模型未下载 | 提示首次运行需下载，退出码 3 |
| 服务器超时 | 客户端重试 3 次，每次间隔 5 秒 |

---

## What this skill does NOT do

- 不训练或微调模型（使用预训练量化模型）
- 不生成论文摘要以外的原创内容
- 不替代人类审阅（标注仅供参考，需自行判断）
- 不处理中文论文（本 Skill 面向英文文献）
- 不做 plagiarism 检测
