"""استخراج متن از فایل‌های آپلودشده (PDF / DOCX / TXT / تصویر) با OCR اختیاری برای اسناد اسکن‌شده."""

import io
import logging
import os

from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)

OCR_LANGUAGES = os.getenv("MIZAN_OCR_LANGUAGES", "fas+eng")
OCR_MAX_PAGES = int(os.getenv("MIZAN_OCR_MAX_PAGES", "20"))
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")


class UnsupportedFileTypeError(ValueError):
    pass


def extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()

    if lower.endswith(".pdf"):
        return _extract_pdf(content)
    if lower.endswith(".docx"):
        return _extract_docx(content)
    if lower.endswith((".txt", ".md")):
        return content.decode("utf-8", errors="ignore")
    if lower.endswith(IMAGE_EXTENSIONS):
        return _ocr_image_bytes(content)

    raise UnsupportedFileTypeError(
        f"پسوند فایل «{filename}» پشتیبانی نمی‌شود. فرمت‌های مجاز: pdf, docx, txt, md, png, jpg, jpeg, tif, tiff, bmp, webp"
    )


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return text or _ocr_pdf(content)


def _extract_docx(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    return "\n".join(p.text for p in document.paragraphs).strip()


def _ocr_image_bytes(content: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("OCR dependencies are not installed")
        return ""

    try:
        with Image.open(io.BytesIO(content)) as image:
            return pytesseract.image_to_string(image, lang=OCR_LANGUAGES).strip()
    except (OSError, pytesseract.TesseractError):
        logger.warning("Image OCR failed", exc_info=True)
        return ""


def _ocr_pdf(content: bytes) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
    except ImportError:
        logger.warning("OCR dependencies are not installed")
        return ""

    try:
        pages = convert_from_bytes(content, last_page=OCR_MAX_PAGES)
        return "\n".join(pytesseract.image_to_string(page, lang=OCR_LANGUAGES) for page in pages).strip()
    except Exception:
        logger.warning("PDF OCR failed", exc_info=True)
        return ""
