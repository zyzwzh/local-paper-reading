# local-paper-reading Skill

## 何时触发

当用户的消息匹配以下任一条件时，触发 local-paper-reading Skill：

### 中文触发词
- 找论文 / 搜论文 / 搜索论文 / 读论文 / 帮我读懂
- 标注论文 / 标注文献 / 逐段翻译
- 我想了解 XXX（XXX 是技术主题）
- 帮我读这篇 PDF / 帮我读这篇论文

### 英文触发词
- find/read/search/annotate papers
- translate this paper paragraph by paragraph
- I want to learn about XXX

### 关键词
arXiv / OpenVINO / 英特尔 / intel / AIPC / 本地 / 离线 / offline

## 调用方式

唯一入口：`scripts\run.ps1`

```powershell
# 搜索+标注
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "我想了解 Transformer"

# 只搜索
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "search deep learning" --search-only

# 标注本地文件
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "C:\path\to\paper.pdf"

# 指定深度：intensive(精读) / skimming(泛读) / overview(速览)
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" "C:\path\to\paper.pdf" --depth intensive

# 续传下载 / 清除缓存
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" --continue
powershell -ExecutionPolicy Bypass -File "scripts\run.ps1" --clear-cache
```

## 返回值处理

输出 JSON 格式。检查 `ok` 字段：`true` 成功，`false` 失败。退出码 3 = 模型下载中，运行 `--continue`。

## 注意事项

- 首次运行下载翻译模型（约 200MB）
- 所有推理本地完成，不上传云端
- `scripts\run.ps1` 是唯一入口
