"""استخراج متن از فایل‌های آپلودشده (PDF / DOCX / TXT)."""

import io

from docx import Document
from pypdf import PdfReader


class UnsupportedFileTypeError(ValueError):
    pass


def extract_text(filename: str, content: bytes) -> str:
    """متن خام را از محتوای فایل استخراج می‌کند بر اساس پسوند فایل."""

    lower = filename.lower()

    if lower.endswith(".pdf"):
        return _extract_pdf(content)
    if lower.endswith(".docx"):
        return _extract_docx(content)
    if lower.endswith((".txt", ".md")):
        return content.decode("utf-8", errors="ignore")

    raise UnsupportedFileTypeError(
        f"پسوند فایل «{filename}» پشتیبانی نمی‌شود. فرمت‌های مجاز: pdf, docx, txt, md"
    )


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _extract_docx(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    paragraphs = [p.text for p in document.paragraphs]
    return "\n".join(paragraphs).strip()
