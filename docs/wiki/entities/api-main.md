# API — FastAPI App

> لایهٔ HTTP میزان؛ نقطهٔ ورود آپلود سند و بازگرداندن تحلیل ریسک.

## مسئولیت‌ها
- `GET /health` — health check ساده (`{"status": "ok"}`)، بدون auth
- `POST /analyze` — دریافت فایل (multipart) + فیلدهای اختیاری پروفایل سازمان، بازگرداندن `RiskAnalysisResult`. پشت `require_api_key` (هدر `X-API-Key`).
- اعتبارسنجی: فایل خالی → 400، حجم بیش از `MIZAN_MAX_UPLOAD_BYTES` → 413، فرمت پشتیبانی‌نشده → 400، متن استخراج‌نشده (مثلاً PDF اسکن‌شده) → 422
- Auth: `require_api_key` dependency — اگر `MIZAN_API_KEY` ست نشده (فقط در `ENVIRONMENT=development` ممکن است)، بدون auth رد می‌شود؛ در غیر این صورت هدر `X-API-Key` باید دقیقاً برابر باشد وگرنه 401.
- Startup fail-closed: اگر `ENVIRONMENT=production` باشد و `MIZAN_API_KEY` یا `CORS_ORIGINS` ست نشده باشند، اپ اصلاً بالا نمی‌آید (`RuntimeError`).
- CORS: allowlist صریح از `CORS_ORIGINS` (comma-separated)؛ در dev پیش‌فرض `localhost:3000`/`127.0.0.1:3000`؛ `allow_credentials=False`، فقط متدهای `GET`/`POST` و هدرهای `Content-Type`/`X-API-Key`.

## ورودی `/analyze`
| فیلد | نوع | الزامی |
|---|---|---|
| `X-API-Key` (header) | str | در production همیشه، در dev فقط اگر `MIZAN_API_KEY` ست شده |
| `file` | UploadFile (pdf/docx/txt/md, ≤`MIZAN_MAX_UPLOAD_BYTES`) | بله |
| `industry` | str | خیر |
| `employee_count` | int | خیر |
| `contractor_ratio_pct` | float | خیر |
| `monthly_revenue_toman` | float | خیر |

## Environment Variables
| متغیر | پیش‌فرض | نکته |
|---|---|---|
| `ENVIRONMENT` | `development` | `production` fail-closed را فعال می‌کند |
| `MIZAN_API_KEY` | (خالی) | الزامی در production |
| `CORS_ORIGINS` | dev: `localhost:3000`/`127.0.0.1:3000` | الزامی و بدون wildcard در production |
| `MIZAN_MAX_UPLOAD_BYTES` | `15728640` (۱۵MB) | باعث 413 در صورت عبور |

## وابستگی‌ها
- [[entities/document-parser]] — استخراج متن از فایل آپلودشده
- [[entities/risk-engine]] — تحلیل ریسک روی متن استخراج‌شده
- [[entities/schemas]] — `OrgProfile`, `RiskAnalysisResult`
- [[concepts/risk-analysis-flow]] — جریان کامل درخواست

## قراردادها / Edge cases
- محتوای فایل با `await file.read()` کامل در حافظه بافر می‌شود، **بعد از آن** در برابر `MIZAN_MAX_UPLOAD_BYTES` چک می‌شود — یعنی بدنه قبل از رد شدن به‌طور کامل خوانده شده (هنوز چک `Content-Length` قبل از خواندن انجام نمی‌شود؛ نقطهٔ باقی‌ماندهٔ TASKS.md P1-11).
- بدون rate-limit — فاز بعد.
- بدون Dockerfile/CI فعلاً.

## منابع کد
- `backend/app/main.py:36` — endpoint `/analyze`
- `backend/app/main.py:31` — endpoint `/health`
