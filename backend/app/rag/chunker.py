"""按段落优先的文本切片：不概括、不改写原文，仅按长度组织上下文片段。"""
from app.rag.types import ParsedBlock, TextChunk


def _split_long_block(block: ParsedBlock, max_chars: int, overlap: int) -> list[TextChunk]:
    chunks = []
    start = 0
    part = 1
    while start < len(block.text):
        end = min(start + max_chars, len(block.text))
        chunks.append(
            TextChunk(
                content=block.text[start:end],
                page_or_section=block.page_or_section,
                metadata={"part": part, "split_from_long_paragraph": True},
            )
        )
        if end == len(block.text):
            break
        start = max(end - overlap, start + 1)
        part += 1
    return chunks


def chunk_blocks(
    blocks: list[ParsedBlock],
    target_chars: int = 500,
    max_chars: int = 800,
    overlap: int = 80,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_section = ""
    current_length = 0

    def flush() -> None:
        nonlocal current_parts, current_length
        content = "\n".join(current_parts).strip()
        if content:
            chunks.append(TextChunk(content=content, page_or_section=current_section, metadata={"part": 1}))
        current_parts = []
        current_length = 0

    for block in blocks:
        text = block.text.strip()
        if not text:
            continue
        if len(text) > max_chars:
            flush()
            long_chunks = _split_long_block(block, max_chars, overlap)
            for chunk in long_chunks:
                chunk.page_or_section = chunk.page_or_section or block.page_or_section
            chunks.extend(long_chunks)
            current_section = block.page_or_section
            continue
        if current_parts and current_length + len(text) + 1 > target_chars:
            flush()
        if not current_parts:
            current_section = block.page_or_section
        current_parts.append(text)
        current_length += len(text) + 1
        if current_length >= max_chars:
            flush()
    flush()
    return chunks