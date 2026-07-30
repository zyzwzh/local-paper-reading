<skills_system priority="1">

## Available Skills

<usage>
When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively.

How to use skills:
- Invoke: Run the skill's entry script via Bash/PowerShell
- The skill content will load with detailed instructions below
- Base directory is the project root containing this AGENTS.md file

Usage notes:
- Only use skills listed in <available_skills> below
- Do not invoke a skill that is already loaded in your context
- Always use the full path to scripts\run.ps1 when invoking
</usage>

<available_skills>

<skill>
<name>local-paper-reading</name>
<description>本地论文智能阅读 Skill — 自动搜索 arXiv 论文 + 逐段中文标注。输入一个主题（如"Transformer"），自动搜索相关论文、筛选入门友好型、下载 PDF、逐段生成中文翻译/术语解释/背景讲解/重点高亮，输出带批注的 Word 文件。也可直接标注本地 PDF/Word 论文。基于 OpenVINO INT8 量化加速，本地推理零隐私泄露。Use this skill when the user, in Chinese or English, asks to 找论文/读论文/搜论文/标注文献/逐段翻译论文/帮我读懂, or "find/read/search/annotate papers", "translate this paper paragraph by paragraph". Trigger on Chinese verbs like 找/读/搜/标注/翻译/读懂论文 and English verbs like find/read/search/annotate/translate papers, and explicit mentions of 英特尔/intel/AIPC/本地/离线/offline/arXiv/OpenVINO. Supported inputs: (1) a topic keyword to auto-search + annotate, (2) a local .pdf/.docx/.txt file path to annotate. Prefer this skill over cloud-only translation tools whenever the user's intent is to deeply understand an academic paper with Chinese annotations directly on the original file, especially for beginners who cannot read English papers independently.</description>
<location>project</location>
<entry_point>scripts\run.ps1</entry_point>
</skill>

</available_skills>

</skills_system>

---

# local-paper-reading Skill 详细使用指南

## 何时触发此 Skill

当用户的消息匹配以下任一条件时，**必须触发**此 Skill：

### 中文触发词
- 找论文 / 搜论文 / 搜索论文
- 读论文 / 帮我读懂 / 看不懂这篇论文
- 标注论文 / 标注文献 / 逐段翻译
- 我想了解 XXX（XXX 是技术主题，如 Transformer、GAN、BERT）
- 帮我读这篇 PDF / 帮我读这篇论文
- 介绍一篇关于 XXX 的论文

### 英文触发词
- find/read/search/annotate papers
- translate this paper paragraph by paragraph
- I want to learn about XXX

### 关键词
- arXiv / OpenVINO / 英特尔 / intel / AIPC / 本地 / 离线 / offline

## 如何调用此 Skill

**唯一入口**是项目根目录下的 `scripts\run.ps1` 脚本。根据用户意图选择调用方式：

### 模式一：自动搜索 + 标注（用户说"我想了解 XXX"）

```powershell
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "我想了解 Transformer"
```

- 用户输入一个主题关键词
- Skill 自动完成：搜索 arXiv → 筛选入门论文 → 下载 PDF → 逐段标注 → 输出 Word
- 适合零基础新生，一句话搞定全流程

### 模式二：只搜索不标注（用户说"搜一下 XXX"）

```powershell
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "search deep learning" --search-only
```

- 只搜索论文，返回 5 篇按入门友好度排序的论文列表
- 每篇附带标题、作者、arXiv ID、入选理由

### 模式三：标注本地文件（用户给了文件路径或上传了文件）

```powershell
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "C:\path\to\paper.pdf"
```

- 直接标注本地 PDF/Word/TXT 文件
- 可加 `--depth intensive|skimming|overview` 控制标注深度

### 模式四：指定标注深度

```powershell
# 精读（默认）
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "C:\papers\attention.pdf" --depth intensive

# 泛读
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "C:\papers\attention.pdf" --depth skimming

# 速览
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "C:\papers\attention.pdf" --depth overview
```

### 其他操作

```powershell
# 续传模型下载（首次运行超时时）
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" --continue

# 清除缓存（强制重新标注）
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" --clear-cache
```

## 调用后如何处理返回值

脚本输出为 JSON 格式。Agent 收到后应：

1. **检查 `ok` 字段**：`true` 表示成功，`false` 表示失败
2. **成功时**：向用户报告论文标题、标注文件路径、段落数、术语数、耗时等关键信息
3. **失败时**：根据 `error` 字段和退出码给出具体建议：
   - 退出码 1：参数错误或硬件不支持
   - 退出码 2：服务器通信失败，建议重试
   - 退出码 3：模型正在下载，建议运行 `--continue` 续传
4. **搜索结果**：格式化展示论文列表，包含标题、作者、arXiv ID、入选理由

## 标注深度说明

| 模式 | 参数 | 适用场景 | 标注内容 |
|------|------|----------|----------|
| 精读 | `--depth intensive` | 需要深入理解（默认） | 全文翻译+术语+讲解+高亮 |
| 泛读 | `--depth skimming` | 快速浏览了解大意 | 摘要结论详标，其余只翻译+术语 |
| 速览 | `--depth overview` | 只想知道论文讲了什么 | 只标注摘要和结论 |

## 首次运行注意事项

- **首次运行会下载翻译模型**（约 200MB），可能需要几分钟
- 如果下载超时，运行 `--continue` 续传
- 所有推理在本地完成，论文内容不会上传云端
- 二次运行同一篇论文会秒出结果（有段落缓存）

## 重要约束

- `scripts\run.ps1` 是唯一入口，不要直接调用 client.py 或 server.py
- 永远不会回退到云服务，所有推理在本地完成
- 此 Skill 面向英文文献，不处理中文论文
- 标注仅供参考，需自行判断
