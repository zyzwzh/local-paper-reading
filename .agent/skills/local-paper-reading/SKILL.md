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

## 三种标注深度

| 模式 | 命令参数 | 适用场景 | 标注内容 |
|------|----------|----------|----------|
| 精读 | `--depth intensive` | 需要深入理解（默认） | 全文翻译+术语+讲解+高亮 |
| 泛读 | `--depth skimming` | 快速浏览了解大意 | 摘要结论详标，其余只翻译+术语 |
| 速览 | `--depth overview` | 只想知道论文讲了什么 | 只标注摘要和结论 |

---

## 退出码约定

| 退出码 | 含义 | 用户操作 |
|--------|------|----------|
| 0 | 成功 | — |
| 1 | 一般错误（参数错误/硬件不支持） | 检查输入和硬件 |
| 2 | 连接错误（服务器通信失败） | 重试，或检查服务器状态 |
| 3 | 模型下载中 | 运行 `--continue` 续传 |
