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
    text = "\n".join(text_parts).strip()
    return _truncate(text), pages


def parse_docx(path: Path) -> tuple[str, int]:
    # Word/DOCX: нормальное количество страниц вытащить нельзя -> ставим 1
    document = Document(str(path))

    parts: list[str] = []
    for p in document.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)

    text = "\n".join(parts).strip()
    return _truncate(text), 1


def parse_document(path: Path) -> tuple[str, int]:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(path)

    # ВАЖНО: python-docx НЕ читает .doc (старый Word). Только .docx.
    # Поэтому .doc — сразу ошибка, чтобы было понятно почему не работает.
    if suffix == ".docx":
        return parse_docx(path)

    if suffix == ".doc":
        raise ValueError("Формат .doc (старый Word) не поддерживается. Сохрани файл как .docx.")

    raise ValueError("Неподдерживаемый формат файла. Поддерживаются: .pdf, .docx")

