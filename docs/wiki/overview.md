# Overview — میزان (Mizan)

**میزان** کوپایلوت هوشمند مدیریت ریسک‌های حقوقی، مالیاتی، تأمین‌اجتماعی و قراردادی برای سازمان‌های ایرانی است.
هدف: قبل از بحران (جریمه، شکایت، بدهی) ریسک‌های بیرونی سازمان را از دل اسناد و قراردادها قابل مشاهده و قابل اقدام کند.
میزان جایگزین مشاور حقوقی نیست — لایه‌ی هشدار زودهنگام و اولویت‌بندی است.

## وضعیت فعلی: MVP فاز اول
جریان پیاده‌سازی‌شده: **آپلود سند → استخراج متن → تحلیل ریسک → خروجی ساختاریافته**.
دیتابیس، پایگاه دانش قانونی (RAG)، Decision Log و Dashboard هنوز پیاده‌سازی نشده‌اند (نقشه‌راه در `docs/PRD.md`).

## اجزای اصلی
| جزء | فایل | نقش |
|---|---|---|
| API | `backend/app/main.py` | FastAPI؛ endpoint های `/health` و `/analyze` |
| Document Parser | `backend/app/document_parser.py` | استخراج متن از PDF/DOCX/TXT/MD |
| Risk Engine | `backend/app/risk_engine.py` | پرامپت‌سازی برای LLM + fallback قاعده‌محور |
| LLM Client | `backend/app/llm_client.py` | کلاینت سبک، سازگار با OpenAI Chat Completions، قابل‌تعویض از طریق env |
| Schemas | `backend/app/schemas.py` | مدل‌های Pydantic ورودی/خروجی |
| Landing | `landing/index.html` + `styles.css` | صفحه معرفی محصول (استاتیک، RTL) |

جزئیات کامل هر جزء: [[index]].

## تصمیم معماری کلیدی
موتور ریسک همیشه کار می‌کند — حتی بدون `LLM_API_KEY` — چون یک fallback قاعده‌محور (keyword-based) دارد.
این یعنی MVP بدون هیچ کلید API قابل اجرا و تست است. جزئیات: [[concepts/llm-fallback-pattern]].

## Stack
FastAPI (Python) · Pydantic · pypdf/python-docx برای پارس سند · LLM از طریق env قابل‌تعویض (OpenAI-compatible).
دیتابیس/storage/RBAC هنوز اضافه نشده‌اند (فاز بعد — نگاه کن `docs/ARCHITECTURE.md` بخش ۴ و ۵).

## امنیت (اضافه‌شده بعد از MVP اول)
`/analyze` پشت auth (`X-API-Key` / `MIZAN_API_KEY`) است، CORS به allowlist صریح محدود شده، سقف حجم آپلود (`MIZAN_MAX_UPLOAD_BYTES`) دارد،
و پرامپت LLM دفاع صریح در برابر prompt injection دارد. در `ENVIRONMENT=production` بدون `MIZAN_API_KEY`/`CORS_ORIGINS` اپ اصلاً بالا نمی‌آید (fail-closed).
جزئیات: [[entities/api-main]], [[entities/risk-engine]].

## نقاط ریسک باز (فنی، نه محصولی)
- بدون CI، بدون Dockerfile، بدون license.
- چک سایز آپلود بعد از خواندن کامل بدنه انجام می‌شود، نه قبل از آن (چک `Content-Length` پیشین هنوز اضافه نشده).
- `mailto:hello@mizan.ai` در لندینگ placeholder است.
- جزئیات کامل: [[log]] و بک‌لاگ تسک در ریشه‌ی حساب گیت‌هاب (`TASKS.md`، آیتم‌های P1-11 و P3-6).

## پیوندهای مهم
- ریپو: `github.com/massoudsh/mizan-legal-copilot` (private)
- PRD: `docs/PRD.md`
- معماری: `docs/ARCHITECTURE.md`
- GitHub Wiki: هنوز غیرفعال است — تلاش برای فعال‌سازی خودکار از طریق API ناموفق بود (`has_wiki` toggle نمی‌شود). برای فعال‌سازی: تنظیمات ریپو → تیک «Wikis» → ساخت اولین صفحه (یک‌بار، دستی). بعد از آن این ویکی محلی (`docs/wiki/`) می‌تواند در آن sync شود.
