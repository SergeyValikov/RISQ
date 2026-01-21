from __future__ import annotations

from pathlib import Path

import pdfplumber
from docx import Document

MAX_CHARS = 200_000


def _truncate(text: str) -> str:
    return text[:MAX_CHARS]


def parse_pdf(path: Path) -> tuple[str, int]:
    text_parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        pages = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return _truncate("\n".join(text_parts)), pages


def parse_docx(path: Path) -> tuple[str, int]:
    document = Document(path)
    text_parts = [paragraph.text for paragraph in document.paragraphs]
    text = "\n".join(text_parts)
    return _truncate(text), 1


def parse_document(path: Path) -> tuple[str, int]:
    if path.suffix.lower() == ".pdf":
        return parse_pdf(path)
    if path.suffix.lower() in {".docx", ".doc"}:
        return parse_docx(path)
    raise ValueError("Неподдерживаемый формат файла")
