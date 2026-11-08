"""PDF / DOCX / TXT 文档解析与文本清洗，不改动评价标准含义。"""
import re
import unicodedata
from pathlib import Path

import pymupdf
from docx import Document

from app.core.exceptions import AppError
from app.rag.types import ParsedBlock

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(character if unicodedata.category(character) != "Cc" or character in "\n\t" else " " for character in text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _paragraph_blocks(text: str, section: str) -> list[ParsedBlock]:
    return [ParsedBlock(text=part, page_or_section=section) for part in re.split(r"\n\s*\n", text) if clean_text(part)]


def parse_pdf(path: Path) -> tuple[list[ParsedBlock], dict]:
    blocks: list[ParsedBlock] = []
    with pymupdf.open(path) as document:
        page_count = document.page_count
        for page_index, page in enumerate(document, start=1):
            text = clean_text(page.get_text("text"))
            for paragraph in _paragraph_blocks(text, f"第 {page_index} 页"):
                paragraph.text = clean_text(paragraph.text)
                if paragraph.text:
                    blocks.append(paragraph)
    return blocks, {"parser": "PyMuPDF", "page_count": page_count}


def parse_docx(path: Path) -> tuple[list[ParsedBlock], dict]:
    document = Document(path)
    blocks: list[ParsedBlock] = []
    current_section = ""
    paragraph_count = 0
    for paragraph in document.paragraphs:
        text = clean_text(paragraph.text)
        if not text:
            continue
        paragraph_count += 1
        style_name = getattr(getattr(paragraph, "style", None), "name", "") or ""
        is_heading = style_name.lower().startswith("heading") or "标题" in style_name
        if is_heading:
            current_section = text
        blocks.append(
            ParsedBlock(
                text=text,
                page_or_section=current_section or f"段落 {paragraph_count}",
                is_heading=is_heading,
            )
        )
    for table_index, table in enumerate(document.tables, start=1):
        for row in table.rows:
            text = clean_text(" | ".join(cell.text for cell in row.cells))
            if text:
                blocks.append(ParsedBlock(text=text, page_or_section=f"表格 {table_index}"))
    return blocks, {"parser": "python-docx", "paragraph_count": paragraph_count, "table_count": len(document.tables)}


def parse_txt(path: Path) -> tuple[list[ParsedBlock], dict]:
    raw = path.read_bytes()
    encoding = "utf-8-sig"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        encoding = "gb18030"
        text = raw.decode(encoding)
    blocks = _paragraph_blocks(clean_text(text), "文本章节")
    for block in blocks:
        block.text = clean_text(block.text)
    return [block for block in blocks if block.text], {"parser": "plain-text", "encoding": encoding}


def parse_document(path: Path) -> tuple[list[ParsedBlock], dict]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise AppError("仅支持 PDF、DOCX、TXT 文档")
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix == ".docx":
        return parse_docx(path)
    return parse_txt(path)