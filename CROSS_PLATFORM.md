# 跨平台兼容性说明

本 Skill 已适配主流 AI Agent / IDE 工具，在各平台上的加载机制如下：

## 平台适配总览

| 平台 | 配置文件 | 加载机制 | 状态 |
|------|---------|---------|------|
| **TRAE** | `SKILL.md` | 原生 Skills，设置→规则和技能→导入 | 已适配 |
| **TRAE Work** | `SKILL.md` + `AGENTS.md` | 原生 Skills + 规则文件 | 已适配 |
| **Qoder** | `.qoder/rules/AGENTS.md` | Rules 规则文件 | 已适配 |
| **WorkBuddy** | `SKILL.md` + `AGENTS.md` | 原生 Skills 导入 + 文件夹授权 | 已适配 |
| **Cursor** | `.cursor/rules/local-paper-reading.mdc` | Project Rules (MDC 格式) | 已适配 |
| **Cursor (旧版)** | `.cursorrules` | 根目录规则文件 | 已适配 |
| **Windsurf** | `.windsurfrules` | 根目录规则文件 | 已适配 |
| **Cline** | `.clinerules` | 根目录规则文件 | 已适配 |
| **GitHub Copilot** | `.github/copilot-instructions.md` | 项目指令文件 | 已适配 |
| **Claude Code** | `.claude/skills/` 或 `SKILL.md` | 原生 Skills | 已适配 |
| **OpenSkill 通用** | `.agent/skills/local-paper-reading/SKILL.md` | OpenSkill CLI 安装 | 已适配 |
| **通用 Agent** | `AGENTS.md` | 根目录通用规则文件 | 已适配 |

## 各平台使用方法

### TRAE / TRAE Work

1. 打开 TRAE 客户端
2. 进入「设置 → 规则和技能 → 技能 → 创建」
3. 选择「导入文件」，上传 `SKILL.md`
4. 或直接打开本项目文件夹，TRAE 会自动扫描 `SKILL.md`

### Qoder

1. 在 Qoder 中打开本项目文件夹
2. Qoder 自动读取 `.qoder/rules/AGENTS.md`
3. 在对话框中直接说「我想了解 Transformer」即可触发

### WorkBuddy

1. 在 WorkBuddy 中授权访问本项目所在文件夹
2. WorkBuddy 会读取 `SKILL.md` 和 `AGENTS.md`
3. 或通过 WorkBuddy 的「Skills 导入」功能导入 `SKILL.md`
4. 导入后在对话框中直接说「我想了解 Transformer」

### Cursor

1. 在 Cursor 中打开本项目文件夹
2. Cursor 自动加载 `.cursor/rules/local-paper-reading.mdc`（新版）
3. 旧版 Cursor 读取 `.cursorrules`
4. 在对话框中说「我想了解 Transformer」即可触发

### Windsurf

1. 在 Windsurf 中打开本项目文件夹
2. Windsurf 自动读取 `.windsurfrules`
3. 在对话框中说「我想了解 Transformer」即可触发

### Cline

1. 在 Cline 中打开本项目文件夹
2. Cline 自动读取 `.clinerules`
3. 在对话框中说「我想了解 Transformer」即可触发

### GitHub Copilot

1. 在 VS Code 中安装 GitHub Copilot 扩展
2. 打开本项目文件夹
3. Copilot 自动读取 `.github/copilot-instructions.md`

### Claude Code

1. 使用 Claude Code CLI 打开本项目
2. 自动扫描 `.claude/skills/` 目录
3. 或使用 OpenSkill CLI 安装：`openskills install .`

### OpenSkill CLI（通用安装）

```bash
# 安装 OpenSkill CLI
npm i -g openskills

# 从本地安装 Skill
openskills install .

# 同步到各平台规则文件
openskills sync --output .qoder/rules/AGENTS.md
openskills sync --output AGENTS.md
```

## 统一触发词

无论哪个平台，用户发送以下消息都会触发 Skill：

### 中文
- 「我想了解 Transformer」
- 「找一篇关于 GAN 的论文」
- 「帮我读这篇 PDF」
- 「搜一下深度学习相关的论文」
- 「逐段翻译这篇论文」

### 英文
- "I want to learn about Transformer"
- "find papers about GAN"
- "annotate this paper"
- "search for deep learning papers"

## 文件结构

```
local-paper-reading/
├── SKILL.md                          # TRAE / WorkBuddy / Claude Code 原生格式
├── AGENTS.md                         # 通用 Agent 规则文件
├── .qoder/rules/AGENTS.md            # Qoder 专用
├── .cursor/rules/local-paper-reading.mdc  # Cursor 新版
├── .cursorrules                      # Cursor 旧版
├── .windsurfrules                    # Windsurf
├── .clinerules                       # Cline
├── .github/copilot-instructions.md   # GitHub Copilot
├── .agent/skills/local-paper-reading/SKILL.md  # OpenSkill 通用
├── scripts/
│   ├── run.ps1                       # 唯一入口
│   ├── client.py
│   ├── server.py
│   └── paper_engine.py
├── info.json
├── meta.json
└── requirements.txt
```

## 注意事项

- 所有平台的配置文件内容一致，只是格式适配不同
- 更新 SKILL.md 后，需同步更新各平台规则文件（或使用 `openskills sync`）
- 首次运行需安装 Python 环境：`scripts\install-env.ps1`
- 首次运行会下载翻译模型（约 200MB）
