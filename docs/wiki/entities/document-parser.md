# Document Parser

> استخراج متن خام از فایل آپلودشده، بر اساس پسوند فایل.

## مسئولیت‌ها
- `extract_text(filename, content) -> str` — نقطهٔ ورود؛ بر اساس پسوند فایل به تابع مناسب dispatch می‌کند.
- پشتیبانی فعلی: `.pdf` (via `pypdf.PdfReader`)، `.docx` (via `python-docx`)، `.txt`/`.md` (decode مستقیم UTF-8، با `errors="ignore"`).
- فرمت پشتیبانی‌نشده → `UnsupportedFileTypeError` (زیرکلاس `ValueError`).

## وابستگی‌ها
- استفاده‌شده توسط [[entities/api-main]]
- کتابخانه‌های خارجی: `pypdf`, `python-docx`

## قراردادها / Edge cases
- PDF اسکن‌شده بدون لایهٔ متنی → رشتهٔ خالی برمی‌گردد (نه خطا) — لایهٔ بالادست (`main.py`) این حالت را با 422 مدیریت می‌کند.
- بدون OCR — اسناد اسکن‌شده فعلاً پشتیبانی نمی‌شوند (در PRD به‌عنوان فاز آینده اشاره شده).

## منابع کد
- `backend/app/document_parser.py:13` — `extract_text`
- `backend/app/document_parser.py:30` — `_extract_pdf`
- `backend/app/document_parser.py:36` — `_extract_docx`
