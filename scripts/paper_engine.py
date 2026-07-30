"""
paper_engine.py — 论文搜索 + 文档解析 + 逐段标注引擎

职责：
  1. 搜索 arXiv 论文，筛选入门友好型
  2. 下载 PDF（原子下载 + .partial 续传）
  3. 解析 PDF/Word/TXT，提取段落
  4. 逐段标注（翻译/术语/讲解/高亮）
  5. 写回 Word 文件
"""
import os
import re
import time
import json
import hashlib
import tempfile
import requests
from pathlib import Path

# ============================================================
# 1. arXiv 论文搜索
# ============================================================

ARXIV_API = "http://export.arxiv.org/api/query"

# 入门友好型关键词（标题含这些词的优先推荐）
BEGINNER_KEYWORDS = [
    "survey", "tutorial", "introduction", "gentle", "primer",
    "a guide to", "understanding", "explained", "basics",
    "deep learning", "machine learning", "neural network"
]


def search_papers(query, max_results=20):
    """
    搜索 arXiv 论文，返回排序后的论文列表。

    Returns:
        list: [{"title", "authors", "arxiv_id", "abstract", "published",
                "pdf_url", "entry_reason", "beginner_score"}]
    """
    import xml.etree.ElementTree as ET

    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    resp = requests.get(ARXIV_API, params=params, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    papers = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        arxiv_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
        abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
        published = entry.find("atom:published", ns).text[:10]

        authors = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns)
            if name is not None:
                authors.append(name.text)

        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")

        # 计算入门友好度分数
        beginner_score = 0
        title_lower = title.lower()
        abstract_lower = abstract.lower()

        for kw in BEGINNER_KEYWORDS:
            if kw in title_lower:
                beginner_score += 10
            if kw in abstract_lower:
                beginner_score += 2

        # 短标题加分（通常更概括）
        if len(title.split()) < 10:
            beginner_score += 3

        # 入选理由
        reasons = []
        if any(kw in title_lower for kw in ["survey", "tutorial", "introduction"]):
            reasons.append("综述/教程类，适合入门")
        if beginner_score >= 15:
            reasons.append("入门关键词匹配度高")
        if len(title.split()) < 10:
            reasons.append("标题简洁")
        if not reasons:
            reasons.append("相关度较高")

        papers.append({
            "title": title,
            "authors": ", ".join(authors[:3]),
            "arxiv_id": arxiv_id,
            "abstract": abstract[:200] + "...",
            "published": published,
            "pdf_url": pdf_url,
            "entry_reason": "；".join(reasons),
            "beginner_score": beginner_score,
        })

    # 按入门友好度排序
    papers.sort(key=lambda x: x["beginner_score"], reverse=True)
    return papers


# ============================================================
# 2. PDF 下载（原子下载 + .partial 续传）
# ============================================================

def download_paper(pdf_url, output_dir=None):
    """
    下载论文 PDF，支持断点续传。

    Returns:
        str: 下载后的 PDF 文件路径
    """
    if output_dir is None:
        output_dir = os.path.join(tempfile.gettempdir(), "paper_reading")
    os.makedirs(output_dir, exist_ok=True)

    filename = pdf_url.split("/")[-1] + ".pdf"
    final_path = os.path.join(output_dir, filename)
    partial_path = final_path + ".partial"

    # 已下载完成
    if os.path.exists(final_path):
        return final_path

    # 续传
    existing_size = 0
    if os.path.exists(partial_path):
        existing_size = os.path.getsize(partial_path)

    headers = {}
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"

    resp = requests.get(pdf_url, headers=headers, stream=True, timeout=60)

    mode = "ab" if existing_size > 0 else "wb"
    with open(partial_path, mode) as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    # 原子重命名
    os.rename(partial_path, final_path)
    return final_path


# ============================================================
# 3. 文档解析
# ============================================================

def parse_document(file_path):
    """
    解析 PDF/Word/TXT 文档，提取段落。

    Returns:
        list: [{"index", "text", "section", "style"}]
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext == ".docx":
        return _parse_docx(file_path)
    elif ext == ".txt":
        return _parse_txt(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def _parse_pdf(file_path):
    """解析 PDF，按页提取文本并切段。"""
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    paragraphs = []
    idx = 0

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        raw_paras = re.split(r'\n\s*\n', text)

        for para_text in raw_paras:
            cleaned = para_text.strip()
            if len(cleaned) > 10:  # 跳过过短片段
                paragraphs.append({
                    "index": idx,
                    "text": cleaned,
                    "section": _identify_section(cleaned),
                    "style": "Normal",
                    "page": page_num,
                })
                idx += 1

    return paragraphs


def _parse_docx(file_path):
    """解析 Word 文档，保留段落结构。"""
    from docx import Document

    doc = Document(file_path)
    paragraphs = []
    idx = 0

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append({
                "index": idx,
                "text": text,
                "section": _identify_section(text),
                "style": para.style.name,
            })
            idx += 1

    return paragraphs


def _parse_txt(file_path, encoding="utf-8"):
    """解析纯文本文件，按空行分段。"""
    with open(file_path, "r", encoding=encoding) as f:
        content = f.read()

    raw_paras = re.split(r'\n\s*\n', content)
    paragraphs = []
    idx = 0

    for para_text in raw_paras:
        cleaned = para_text.strip()
        if cleaned:
            paragraphs.append({
                "index": idx,
                "text": cleaned,
                "section": _identify_section(cleaned),
                "style": "Normal",
            })
            idx += 1

    return paragraphs


# ============================================================
# 4. 文献结构识别
# ============================================================

SECTION_PATTERNS = {
    "abstract": [r"^abstract", r"^summary"],
    "introduction": [r"^1\.\s*introduction", r"^introduction"],
    "method": [r"^method", r"^approach", r"^model\s+architect"],
    "experiment": [r"^experiment", r"^evaluation", r"^results"],
    "discussion": [r"^discussion", r"^analysis"],
    "conclusion": [r"^conclusion", r"^concluding"],
    "references": [r"^references", r"^bibliography"],
    "acknowledgments": [r"^acknowledg"],
}


def _identify_section(text):
    """根据段落文本识别所属章节。"""
    first_line = text[:200].lower()
    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, first_line):
                return section
    return "body"


# ============================================================
# 5. 逐段标注生成
# ============================================================

# 标注策略：不同章节用不同深度
SECTION_ANNOTATION_STRATEGY = {
    "abstract":      "full",    # 翻译+术语+讲解+高亮
    "introduction":  "full",
    "method":        "full",
    "experiment":    "translate_terms",  # 翻译+术语
    "discussion":    "translate_explain",
    "conclusion":    "full",
    "references":    "skip",    # 不标注
    "acknowledgments": "skip",
    "body":          "translate_terms",
}


def generate_annotations(paragraphs, depth="intensive", infer_callback=None):
    """
    逐段生成标注。

    Args:
        paragraphs: 解析后的段落列表
        depth: intensive(精读) / skimming(泛读) / overview(速览)
        infer_callback: 推理回调函数，接收 (text, task_type) 返回结果

    Returns:
        list: 标注后的段落列表，每段含 original/translation/terms/explanation/highlights
    """
    annotated = []
    stats = {"total": 0, "translated": 0, "terms": 0, "highlighted": 0}

    for para in paragraphs:
        section = para["section"]
        strategy = SECTION_ANNOTATION_STRATEGY.get(section, "translate_terms")

        # 速览模式：只标注摘要和结论
        if depth == "overview" and section not in ("abstract", "conclusion"):
            continue

        # 泛读模式：非摘要/结论只翻译
        if depth == "skimming" and section not in ("abstract", "conclusion", "introduction"):
            strategy = "translate_only"

        if strategy == "skip":
            continue

        annotation = {
            "index": para["index"],
            "original": para["text"],
            "section": section,
            "translation": "",
            "terms": [],
            "explanation": "",
            "highlights": [],
        }

        # 调用推理回调（或用模拟数据）
        if infer_callback:
            if strategy in ("full", "translate_terms", "translate_only", "translate_explain"):
                annotation["translation"] = infer_callback(para["text"], "translate")

            if strategy in ("full", "translate_terms"):
                annotation["terms"] = infer_callback(para["text"], "terms")

            if strategy in ("full", "translate_explain"):
                annotation["explanation"] = infer_callback(para["text"], "explain")

            if strategy == "full":
                annotation["highlights"] = infer_callback(para["text"], "highlight")
        else:
            # 模拟标注（演示模式）
            annotation["translation"] = f"[翻译] {para['text'][:50]}..."
            annotation["terms"] = [{"en": "term", "zh": "术语", "explain": "解释"}]
            annotation["explanation"] = "[讲解] 本段属于" + section + "部分。"
            annotation["highlights"] = [para["text"][:30]]

        annotated.append(annotation)
        stats["total"] += 1
        if annotation["translation"]:
            stats["translated"] += 1
        if annotation["terms"]:
            stats["terms"] += len(annotation["terms"])
        if annotation["highlights"]:
            stats["highlighted"] += len(annotation["highlights"])

    return annotated, stats


# ============================================================
# 6. 写回 Word 文件
# ============================================================

def write_annotated_docx(annotated_paragraphs, output_path, paper_title="标注论文", paper_source=""):
    """
    将标注结果写入 Word 文件。

    Args:
        annotated_paragraphs: generate_annotations 的返回结果
        output_path: 输出文件路径
        paper_title: 论文标题
        paper_source: 论文来源（如 arXiv ID）
    """
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()

    # 颜色常量
    COLOR_TRANSLATION = RGBColor(0x00, 0x66, 0xCC)
    COLOR_TERM = RGBColor(0x00, 0x80, 0x00)
    COLOR_EXPLANATION = RGBColor(0x66, 0x66, 0x66)
    COLOR_TITLE = RGBColor(0x1a, 0x1a, 0x2e)

    def set_highlight(run, color="yellow"):
        rPr = run._element.get_or_add_rPr()
        highlight = OxmlElement("w:highlight")
        highlight.set(qn("w:val"), color)
        rPr.append(highlight)

    def set_shading(paragraph, color="F0F0F0"):
        pPr = paragraph._element.get_or_add_pPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), color)
        pPr.append(shading)

    # 标题
    title = doc.add_heading("", level=0)
    run = title.add_run(paper_title)
    run.font.size = Pt(18)
    run.font.color.rgb = COLOR_TITLE
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if paper_source:
        src = doc.add_paragraph()
        src.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = src.add_run(f"来源: {paper_source}")
        run.font.size = Pt(10)
        run.font.color.rgb = COLOR_EXPLANATION

    doc.add_paragraph()

    # 逐段写入
    for ann in annotated_paragraphs:
        # 原文
        p = doc.add_paragraph()
        run = p.add_run(ann["original"])
        run.font.name = "Times New Roman"
        run.font.size = Pt(10.5)

        # 翻译
        if ann["translation"]:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            label = p.add_run("【翻译】")
            label.font.size = Pt(10.5)
            label.font.color.rgb = COLOR_TRANSLATION
            label.font.bold = True
            run = p.add_run(ann["translation"])
            run.font.size = Pt(10.5)
            run.font.color.rgb = COLOR_TRANSLATION
            run.font.italic = True

        # 术语
        if ann["terms"]:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            label = p.add_run("【术语】")
            label.font.size = Pt(10.5)
            label.font.color.rgb = COLOR_TERM
            label.font.bold = True
            for term in ann["terms"]:
                if isinstance(term, dict):
                    term_run = p.add_run(
                        f"\n  • {term.get('en', '')}  {term.get('zh', '')}：{term.get('explain', '')}"
                    )
                else:
                    term_run = p.add_run(f"\n  • {term}")
                term_run.font.size = Pt(10)
                term_run.font.color.rgb = COLOR_TERM

        # 讲解
        if ann["explanation"]:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            label = p.add_run("【讲解】")
            label.font.size = Pt(10.5)
            label.font.color.rgb = COLOR_EXPLANATION
            label.font.bold = True
            run = p.add_run(ann["explanation"])
            run.font.size = Pt(10.5)
            run.font.color.rgb = COLOR_EXPLANATION
            set_shading(p)

        # 分隔线
        divider = doc.add_paragraph()
        run = divider.add_run("─" * 50)
        run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        run.font.size = Pt(9)

    doc.save(output_path)
    return output_path


# ============================================================
# 7. 完整流程：搜索 → 下载 → 标注 → 输出
# ============================================================

def search_and_annotate(query, output_dir=None, depth="intensive", infer_callback=None):
    """
    完整流程：搜索论文 → 筛选 → 下载 → 标注 → 输出 Word。

    Args:
        query: 搜索关键词
        output_dir: 输出目录
        depth: 标注深度
        infer_callback: 推理回调

    Returns:
        dict: 结果摘要
    """
    t0 = time.time()

    if output_dir is None:
        output_dir = os.path.join(os.path.expanduser("~"), "Documents", "annotated_papers")
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: 搜索
    print(f"[paper_engine] 搜索 arXiv: {query}")
    papers = search_papers(query, max_results=20)
    if not papers:
        return {"ok": False, "error": f"未找到关于 '{query}' 的论文"}

    # Step 2: 选择最佳论文（入门友好度最高）
    best = papers[0]
    print(f"[paper_engine] 选中: {best['title']} (score={best['beginner_score']})")

    # Step 3: 下载 PDF
    if best["pdf_url"]:
        print(f"[paper_engine] 下载 PDF: {best['pdf_url']}")
        pdf_path = download_paper(best["pdf_url"])
    else:
        return {"ok": False, "error": "论文无 PDF 链接"}

    # Step 4: 解析
    print(f"[paper_engine] 解析文档: {pdf_path}")
    paragraphs = parse_document(pdf_path)
    print(f"[paper_engine] 提取段落: {len(paragraphs)}")

    # Step 5: 标注
    print(f"[paper_engine] 逐段标注 (depth={depth})")
    annotated, stats = generate_annotations(paragraphs, depth, infer_callback)

    # Step 6: 写回 Word
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", best["title"][:50])
    output_path = os.path.join(output_dir, f"annotated_{safe_title}.docx")
    write_annotated_docx(annotated, output_path, best["title"], f"arXiv:{best['arxiv_id']}")

    elapsed = time.time() - t0
    result = {
        "ok": True,
        "论文标题": best["title"],
        "论文来源": f"arXiv:{best['arxiv_id']}",
        "论文作者": best["authors"],
        "入选理由": best["entry_reason"],
        "标注文件": output_path,
        "标注段落数": stats["total"],
        "术语数": stats["terms"],
        "高亮句数": stats["highlighted"],
        "耗时": f"{elapsed:.1f}秒",
        "标注深度": {"intensive": "精读", "skimming": "泛读", "overview": "速览"}.get(depth, depth),
    }

    print(f"[paper_engine] 完成: {output_path}")
    return result


def annotate_file(file_path, output_dir=None, depth="intensive", infer_callback=None):
    """
    直接标注本地文件。

    Returns:
        dict: 结果摘要
    """
    t0 = time.time()

    if output_dir is None:
        output_dir = os.path.join(os.path.expanduser("~"), "Documents", "annotated_papers")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(file_path):
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    # 解析
    print(f"[paper_engine] 解析文档: {file_path}")
    paragraphs = parse_document(file_path)
    print(f"[paper_engine] 提取段落: {len(paragraphs)}")

    # 标注
    print(f"[paper_engine] 逐段标注 (depth={depth})")
    annotated, stats = generate_annotations(paragraphs, depth, infer_callback)

    # 写回 Word
    base_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f"annotated_{base_name}.docx")
    write_annotated_docx(annotated, output_path, base_name, file_path)

    elapsed = time.time() - t0
    result = {
        "ok": True,
        "论文标题": base_name,
        "论文来源": file_path,
        "标注文件": output_path,
        "标注段落数": stats["total"],
        "术语数": stats["terms"],
        "高亮句数": stats["highlighted"],
        "耗时": f"{elapsed:.1f}秒",
        "标注深度": {"intensive": "精读", "skimming": "泛读", "overview": "速览"}.get(depth, depth),
    }

    print(f"[paper_engine] 完成: {output_path}")
    return result
