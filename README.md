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

## تست

```bash
cd backend
python -m pytest -v
ruff check app tests
```
