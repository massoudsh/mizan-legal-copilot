# میزان (Mizan)

کوپایلوت مدیریت ریسک‌های حقوقی و رگولاتوری برای سازمان‌های ایرانی.

## معماری

- `backend/` — FastAPI، OCR، تحلیل ریسک، RBAC و دادهٔ چندمستأجری
- `landing/` — لندینگ RTL، فرم واقعی درخواست دمو و داشبورد وب
- `backend/database/postgres.sql` — schema production برای PostgreSQL، RLS و `pgvector`
- `backend/evals/golden.json` — مجموعهٔ ارزیابی regression برای تحلیل ریسک

## راه‌اندازی محلی

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

در production متغیرهای `MIZAN_API_KEY`، `CORS_ORIGINS` و `MIZAN_DATA_ENCRYPTION_KEY` اجباری هستند.

## امنیت و tenancy

- APIهای سازمانی با `Authorization: Bearer <access token>` محافظت می‌شوند.
- نقش‌ها: `owner`، `admin`، `analyst` و `viewer`؛ هر query سازمانی تنها با `organization_id` استخراج‌شده از توکن اجرا می‌شود.
- ساخت سازمان و صدور توکن یک‌بارمصرف کاربر از endpointهای مدیریتی و با `X-API-Key` انجام می‌شود.
- اطلاعات تماس درخواست دمو با Fernet در SQLite رمزنگاری می‌شوند؛ فقط شناسه و زمان ثبت به client برمی‌گردد.
- connectorها تنها `secret_reference` نگه می‌دارند، نه secret واقعی.

## APIهای اصلی

| مسیر | نقش لازم | کاربرد |
|---|---|---|
| `POST /demo-requests` | عمومی | ثبت امن درخواست دمو با honeypot ضداسپم |
| `POST /admin/organizations` | کلید مدیریتی | ایجاد سازمان |
| `POST /admin/organizations/{id}/users` | کلید مدیریتی | صدور توکن کاربر و تخصیص نقش |
| `PUT/GET /profile` | admin+ / همه | پروفایل ریسک tenant |
| `POST/GET /decisions` | analyst+ / همه | دفتر تصمیم tenant |
| `POST /analyze` | analyst+ | تحلیل سند در بستر tenant |
| `POST/GET /regulations` | admin+ / همه | ingestion نسخه‌دار و بازیابی مقررات معتبر |
| `POST/GET /connectors` | admin | connector مالی یا HR با secret reference |
| `GET /dashboard` | همه | روند تصمیم‌ها، ریسک‌های بحرانی و هشدارها |

## RAG و رصد مقررات

در حالت local، بازیابی مقررات با FTS5 و فیلتر بازهٔ اجرا انجام می‌شود. `backend/database/postgres.sql` مسیر production را با `pgvector`، ایندکس HNSW و RLS آماده می‌کند؛ embeddingها باید هنگام ingestion توسط سرویس embedding سازمان پر شوند. منابع معتبر JSON با `POST /regulatory-sources` ثبت و با اجرای زمان‌بندی‌شدهٔ `python -m app.regulatory_sync` پایش می‌شوند؛ تنها hostهای تعریف‌شده در `MIZAN_REGULATORY_SOURCE_HOSTS` مجازند. نسخهٔ تازه برای همهٔ tenantها هشدار ایجاد می‌کند.

## Observability و کیفیت

- با تنظیم `OTEL_EXPORTER_OTLP_ENDPOINT`، traceهای FastAPI به OTLP صادر می‌شوند.
- CI شامل lint، تست، gitleaks، Dependabot و artifact SBOM CycloneDX است.
- ارزیابی regression: `pytest tests/test_evals.py -v`.

## قابلیت‌های متمایز CLM ایرانی

بررسی رقبا نشان داد بازار ایران بیشتر روی پاسخ‌گویی حقوقی و review سند متمرکز است؛ شکاف قابل‌دفاع، workflow سازمانی contract-lifecycle است. پنج قابلیت اضافه‌شده:

1. `POST/GET /obligations` — تعهدات، مالک و سررسید قابل پیگیری.
2. `POST/GET /reviews` — ارجاع تصمیم به بررسی انسانی و وضعیت approval.
3. `POST /contract-versions` و `GET /contract-diff` — مقایسهٔ نسخه‌های قرارداد در سطح خط.
4. `GET /audit-export` — خروجی کامل تصمیم‌ها، review و تعهدات، بدون سقف ۵۰ رکورد.
5. `trust_score` در مقررات — امتیاز ثبت‌شدهٔ کیفیت منبع در کنار تاریخ اعتبار؛ این امتیاز ارزیابی خودکار اعتبار نیست.

بررسی جدید همیشه `pending` است و فقط به کاربر عضو همان سازمان با نقش قابل‌نوشتن ارجاع می‌شود. `PUT /reviews/{id}` فقط برای بررسی‌کنندهٔ تعیین‌شده مجاز است و نتیجهٔ `approved` یا `rejected` نهایی می‌ماند؛ تغییر مجدد پاسخ ۴۰۹ می‌دهد. `PUT /obligations/{id}/status` وضعیت تعهد را در محدودهٔ همان tenant تغییر می‌دهد. داشبورد وب این کنترل‌ها و دانلود حسابرسی را با توجه به هویت `GET /me` نمایش می‌دهد.

در شروع سرویس، دیتابیس‌های موجود فاقد `trust_score` بدون حذف داده با مقدار پیش‌فرض ۵۰ ارتقا می‌یابند. اتصال‌های SQLite همگی foreign key را اعمال می‌کنند.

این‌ها در کنار درخواست دمو، RBAC، tenant isolation، OCR، connectorهای HR/مالی و داشبورد، میزان را از یک legal chatbot به یک workspace عملیاتی نزدیک می‌کند.

## بررسی ساختار repository

`docs/wiki/` مستندات commit‌شدهٔ repository است و `.noqte/wiki/` context اجرایی پنل؛ این دو نقش متفاوت دارند و حذف یکی بدون مهاجرت integrationها خطرناک است.
در audit فعلی فایل تکراری اجرایی یا flow بلااستفاده پیدا نشد؛ مسیرهای قدیمی سازمانی با API tenant-scoped جایگزین شده‌اند و هیچ `mailto` placeholder در landing باقی نمانده است.
## تست

```bash
cd backend
python -m pytest -v
ruff check app tests
```

تست‌های داشبورد بدون مرورگر، از ریشهٔ پروژه: `node --test landing/dashboard.test.cjs`.