# API — FastAPI App

> لایهٔ HTTP میزان؛ نقطهٔ ورود آپلود سند و بازگرداندن تحلیل ریسک.

## مسئولیت‌ها
- `GET /health` — health check ساده (`{"status": "ok"}`)
- `POST /analyze` — دریافت فایل (multipart) + فیلدهای اختیاری پروفایل سازمان، بازگرداندن `RiskAnalysisResult`
- اعتبارسنجی اولیه: فایل خالی → 400، فرمت پشتیبانی‌نشده → 400، متن استخراج‌نشده (مثلاً PDF اسکن‌شده) → 422
- CORS باز (`allow_origins=["*"]`) — فقط برای فاز MVP

## ورودی `/analyze`
| فیلد | نوع | الزامی |
|---|---|---|
| `file` | UploadFile (pdf/docx/txt/md) | بله |
| `industry` | str | خیر |
| `employee_count` | int | خیر |
| `contractor_ratio_pct` | float | خیر |
| `monthly_revenue_toman` | float | خیر |

## وابستگی‌ها
- [[entities/document-parser]] — استخراج متن از فایل آپلودشده
- [[entities/risk-engine]] — تحلیل ریسک روی متن استخراج‌شده
- [[entities/schemas]] — `OrgProfile`, `RiskAnalysisResult`
- [[concepts/risk-analysis-flow]] — جریان کامل درخواست

## قراردادها / Edge cases
- محتوای فایل با `await file.read()` کامل در حافظه بافر می‌شود — **هیچ چک سایز/Content-Length قبل از خواندن انجام نمی‌شود** (نقطهٔ ریسک شناخته‌شده؛ نگاه کن TASKS.md P1-11).
- بدون auth/rate-limit — فاز بعد.
- بدون Dockerfile/CI فعلاً.

## منابع کد
- `backend/app/main.py:36` — endpoint `/analyze`
- `backend/app/main.py:31` — endpoint `/health`
