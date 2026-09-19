# میزان (Mizan)
### کوپایلوت هوشمند مدیریت ریسک‌های حقوقی و رگولاتوری برای سازمان‌های ایرانی

در ایران فهم قانون کافی نیست؛ سازمان باید بفهمد قانون چطور تفسیر و اجرا می‌شود. میزان لایه‌ای است که قبل از بحران،
ریسک‌های حقوقی، مالیاتی، تأمین‌اجتماعی و قراردادی را از دل اسناد، تصمیم‌ها و رویه‌های اجرایی قابل مشاهده و قابل
اقدام می‌کند.

## مستندات

- [PRD — سند محصول](docs/PRD.md)
- [معماری فنی](docs/ARCHITECTURE.md)

## ساختار پروژه

```
backend/    سرویس MVP تحلیل ریسک (FastAPI) — آپلود سند → تحلیل ریسک
landing/    صفحه معرفی محصول (استاتیک HTML/CSS)
docs/       PRD و معماری فنی
```

## اجرای بک‌اند (MVP)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # اختیاری — بدون کلید LLM هم در حالت fallback قاعده‌محور کار می‌کند
uvicorn app.main:app --reload --port 8000
```

سپس:

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@/path/to/contract.pdf" \
  -F "industry=فناوری اطلاعات" \
  -F "employee_count=25"
```

### اجرای تست‌ها

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v
```

### محدودیت نرخ درخواست

endpoint های سنگین (مثل `/analyze`) محدودیت نرخ درون‌حافظه‌ای دارند که با متغیرهای محیطی تنظیم می‌شود:

| متغیر | پیش‌فرض | توضیح |
|---|---|---|
| `RATE_LIMIT_REQUESTS` | `10` | تعداد مجاز درخواست در هر پنجره |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | طول پنجره به ثانیه |

در صورت عبور از سقف، پاسخ `429` همراه با هدر `Retry-After` برگردانده می‌شود. این شمارنده‌ها
در حافظه‌ی پروسه نگه داشته می‌شوند؛ برای استقرار چند-نمونه‌ای باید به فروشگاه مشترک (مثل Redis) منتقل شوند.

## مشاهده لندینگ

فایل `landing/index.html` را مستقیماً در مرورگر باز کنید — بدون نیاز به build.

## وضعیت پروژه

نسخه‌ی فعلی، **MVP فاز اول** است: آپلود سند → تحلیل ریسک با LLM قابل‌تعویض (یا fallback قاعده‌محور در نبود کلید API).
نقشه‌راه کامل در [PRD](docs/PRD.md) آمده است.
