# میزان (Mizan)
### کوپایلوت هوشمند مدیریت ریسک‌های حقوقی و رگولاتوری برای سازمان‌های ایرانی

در ایران فهم قانون کافی نیست؛ سازمان باید بفهمد قانون چطور تفسیر و اجرا می‌شود. میزان لایه‌ای است که قبل از بحران،
ریسک‌های حقوقی، مالیاتی، تأمین‌اجتماعی و قراردادی را از دل اسناد، تصمیم‌ها و رویه‌های اجرایی قابل مشاهده و قابل
اقدام می‌کند.

## مستندات

- [PRD — سند محصول](docs/PRD.md)
- [معماری فنی](docs/ARCHITECTURE.md)
- [ویکی دانش پروژه](docs/wiki/overview.md) — خلاصهٔ فشردهٔ اجزا/فلوها برای ایجنت‌ها، همیشه به‌روز
- [LICENSE](LICENSE) — Apache-2.0

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
  -H "X-API-Key: $MIZAN_API_KEY" \
  -F "file=@/path/to/contract.pdf" \
  -F "industry=فناوری اطلاعات" \
  -F "employee_count=25"
```

> **امنیت:** endpoint `/analyze` نیازمند هدر `X-API-Key` است. در `ENVIRONMENT=development` اگر `MIZAN_API_KEY` تنظیم نشده باشد، endpoint بدون auth باز می‌ماند (فقط برای dev محلی)؛ در `ENVIRONMENT=production` تنظیم `MIZAN_API_KEY` و `CORS_ORIGINS` الزامی است و بدون آن‌ها سرویس اصلاً بالا نمی‌آید.

> **محدودیت طول سند:** وقتی تحلیل با LLM انجام می‌شود (`LLM_API_KEY` تنظیم‌شده)، فقط **۱۲٬۰۰۰ کاراکتر اول** متن استخراج‌شده به مدل ارسال می‌شود (`backend/app/risk_engine.py`) تا در سقف context/هزینه‌ی مدل بمانیم. برای اسناد طولانی‌تر، بخش‌های بعد از این حد در تحلیل LLM لحاظ نمی‌شوند؛ raw text کامل هنوز برای فراخوانی مستقیم فرمت‌بندی موجود است اما truncate می‌شود. حالت fallback قاعده‌محور (`analysis_mode: "rule_fallback"`) این محدودیت را ندارد و کل متن سند را با regex بررسی می‌کند.

### اجرای تست‌ها

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

CI (GitHub Actions) این تست‌ها را روی هر push/PR به `main` اجرا می‌کند (`.github/workflows/ci.yml`).

### اجرا با Docker

```bash
docker compose up --build
```

سرویس روی `http://localhost:8000` بالا می‌آید (`/health` باید `200` برگرداند). این compose پیش‌فرض‌های dev را ست می‌کند؛ برای production مقادیر `MIZAN_API_KEY`/`CORS_ORIGINS`/`ENVIRONMENT` را از یک secret manager واقعی override کنید (نه commit در `docker-compose.yml`).

## مشاهده لندینگ

فایل `landing/index.html` را مستقیماً در مرورگر باز کنید — بدون نیاز به build.

## وضعیت پروژه

نسخه‌ی فعلی، **MVP فاز اول** است: آپلود سند → تحلیل ریسک با LLM قابل‌تعویض (یا fallback قاعده‌محور در نبود کلید API).
نقشه‌راه کامل در [PRD](docs/PRD.md) آمده است.
