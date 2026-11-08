"""RAG 内部数据结构，不与 API Schema 混用。"""
from dataclasses import dataclass, field


@dataclass
class ParsedBlock:
    text: str
    page_or_section: str = ""
    is_heading: bool = False


@dataclass
class TextChunk:
    content: str
    page_or_section: str
    metadata: dict = field(default_factory=dict)