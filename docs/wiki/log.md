# Log

## [2026-08-16] update | راه‌اندازی اولیهٔ ویکی دانش پروژه بعد از MVP اول (PRD، معماری، backend، لندینگ)
## [2026-08-16] update | sync با کامیت امنیتی خارجی ac168a6 (auth، CORS allowlist، سقف آپلود، لاگ ساختاریافته fallback، دفاع prompt-injection) — api-main و risk-engine و overview به‌روز شدند
## [2026-08-16] update | تلاش برای فعال‌سازی GitHub Wiki از طریق API ناموفق بود (`has_wiki` با PATCH ست نمی‌شود، push به `.wiki.git` → «Repository not found»)؛ نیاز به فعال‌سازی دستی یک‌باره از تنظیمات ریپو + ساخت اولین صفحه — نگاه کن [[overview]]
## [2026-08-16] update | کاربر ویکی گیت‌هاب را دستی فعال کرد و اولین صفحه (Home) را ساخت؛ `.wiki.git` clone شد و کل `docs/wiki/` (overview, index, log, schema, entities/*, concepts/*) به آن push شد — GitHub Wiki اکنون کاملاً sync است
## [2026-08-16] update | پیاده‌سازی آیتم‌های باز TASKS.md برای این ریپو: middleware دو-لایه‌ی محدودیت آپلود (`Content-Length` پیش از خواندن بدنه)، ۱۴ تست جدید (`test_api.py` ۸ مورد، `test_document_parser.py` ۶ مورد)، `backend/Dockerfile` + `docker-compose.yml` با healthcheck، `requirements-dev.txt`، `LICENSE` (Apache-2.0)، مستندسازی truncation ۱۲٬۰۰۰ کاراکتری در README — نگاه کن [[entities/api-main]]
## [2026-08-16] update | فایل `.github/workflows/ci.yml` push نشد چون توکن فعلی scope گیت‌هابی `workflow` ندارد (رد شد با «refusing to allow an OAuth App ... without workflow scope»)؛ فایل محلی موجود است، ثبت شد به‌عنوان GitHub Issue #1 برای اقدام دستی صاحب پروژه
## [2026-08-16] update | ۱۰ ایشوی GitHub ساخته شد برای بک‌لاگ آینده: #1 CI blocked، #2 mailto placeholder، #3-#5 روادمپ v1 (رصد ابلاغیه، Decision Log، پروفایل سازمان پایدار)، #6-#8 روادمپ v2 (داشبورد، یکپارچه‌سازی، RAG)، #9 OCR برای PDF اسکن‌شده، #10 rate limiting
