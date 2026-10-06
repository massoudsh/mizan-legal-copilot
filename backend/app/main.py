"""میزان — MVP سرویس تحلیل ریسک حقوقی/رگولاتوری.

اجرا:
    uvicorn app.main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
from datetime import date

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import storage
from app.document_parser import UnsupportedFileTypeError, extract_text
from app.rate_limit import enforce_rate_limit
from app.risk_engine import analyze_document
from app.schemas import (
    DashboardSummary,
    Decision,
    DecisionInput,
    OrganizationProfile,
    OrganizationProfileInput,
    OrgProfile,
    Regulation,
    RegulationInput,
    RiskAnalysisResult,
)

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_KEY = os.getenv("MIZAN_API_KEY")
MAX_UPLOAD_BYTES = int(os.getenv("MIZAN_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))  # 15MB default

if ENVIRONMENT == "production" and not API_KEY:
    raise RuntimeError(
        "MIZAN_API_KEY must be set in production — /analyze must not be exposed without authentication. "
        "Set ENVIRONMENT=development to bypass this check for local dev."
    )

_cors_origins_env = os.getenv("CORS_ORIGINS", "")
if _cors_origins_env:
    ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
elif ENVIRONMENT == "production":
    raise RuntimeError(
        "CORS_ORIGINS must be set explicitly in production (comma-separated origins) — "
        "wildcard CORS is not allowed. Set ENVIRONMENT=development to bypass this check for local dev."
    )
else:
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

@asynccontextmanager
async def lifespan(_: FastAPI):
    storage.initialize_database()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Mizan — Legal & Regulatory Risk Copilot API",
    description="سرویس تحلیل ریسک حقوقی، مالیاتی، تأمین اجتماعی و قراردادی برای سازمان‌های ایرانی",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def reject_oversized_uploads(request: Request, call_next):
    """رد درخواست‌های آپلود بزرگ بر اساس هدر Content-Length، پیش از این‌که Starlette بدنه‌ی
    multipart را کامل پارس/بافر کند. این چک قبل از هر خواندن بدنه اجرا می‌شود (سطح middleware،
    قبل از resolve شدن dependency ها و parse شدن File(...))."""
    if request.method == "POST" and request.url.path == "/analyze":
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = None
            if declared_size is not None and declared_size > MAX_UPLOAD_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"حجم فایل بیش از حد مجاز است (حداکثر {MAX_UPLOAD_BYTES // (1024 * 1024)}MB)."
                    },
                )
    return await call_next(request)


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Guards state-changing/expensive endpoints. No-op only in explicit local dev without a configured key."""
    if not API_KEY:
        # Only reachable when ENVIRONMENT != production (see startup check above).
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="کلید API نامعتبر یا ارسال‌نشده است.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/analyze",
    response_model=RiskAnalysisResult,
    dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)],
)
async def analyze(
    file: UploadFile = File(..., description="سند/قرارداد (pdf, docx, txt, md, png, jpg, tiff)"),
    industry: str | None = Form(default=None),
    employee_count: int | None = Form(default=None),
    contractor_ratio_pct: float | None = Form(default=None),
    monthly_revenue_toman: float | None = Form(default=None),
    organization_id: str | None = Form(default=None),
) -> RiskAnalysisResult:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="فایل آپلودشده خالی است.")
    if len(content) > MAX_UPLOAD_BYTES:
        # چک اصلی روی Content-Length در سطح middleware (reject_oversized_uploads) و قبل از این
        # خط اجرا می‌شود. این چک دومِ دفاع‌درعمق است برای کلاینت‌هایی که Content-Length
        # نمی‌فرستند (مثلاً chunked transfer-encoding) یا مقدار آن را نادرست اعلام می‌کنند.
        raise HTTPException(
            status_code=413,
            detail=f"حجم فایل بیش از حد مجاز است (حداکثر {MAX_UPLOAD_BYTES // (1024 * 1024)}MB).",
        )

    try:
        text = extract_text(file.filename or "document", content)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="متنی از فایل استخراج نشد. اگر سند اسکن‌شده است، OCR (Tesseract با زبان فارسی) باید روی سرور نصب باشد.",
        )

    stored = storage.get_profile(organization_id) if organization_id else None
    base = stored.model_dump(include=set(OrgProfile.model_fields)) if stored else {}
    submitted = {
        "industry": industry,
        "employee_count": employee_count,
        "contractor_ratio_pct": contractor_ratio_pct,
        "monthly_revenue_toman": monthly_revenue_toman,
    }
    org_profile = OrgProfile(**{**base, **{k: v for k, v in submitted.items() if v is not None}})

    regulations = storage.search_regulations(text[:2000], date.today().isoformat())
    return analyze_document(
        document_name=file.filename or "document",
        document_text=text,
        org_profile=org_profile,
        regulations=regulations,
    )


@app.put("/organizations/profile", response_model=OrganizationProfile, dependencies=[Depends(require_api_key)])
def upsert_profile(profile: OrganizationProfileInput) -> OrganizationProfile:
    return storage.save_profile(profile)


@app.get("/organizations/{organization_id}/profile", response_model=OrganizationProfile, dependencies=[Depends(require_api_key)])
def read_profile(organization_id: str) -> OrganizationProfile:
    profile = storage.get_profile(organization_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="پروفایل سازمان یافت نشد.")
    return profile


@app.post("/decisions", response_model=Decision, status_code=201, dependencies=[Depends(require_api_key)])
def create_decision(decision: DecisionInput) -> Decision:
    return storage.create_decision(decision)


@app.get("/organizations/{organization_id}/decisions", response_model=list[Decision], dependencies=[Depends(require_api_key)])
def read_decisions(organization_id: str, limit: int = Query(default=50, ge=1, le=200)) -> list[Decision]:
    return storage.list_decisions(organization_id, limit)


@app.post("/regulations", response_model=Regulation, status_code=201, dependencies=[Depends(require_api_key)])
def create_regulation(regulation: RegulationInput) -> Regulation:
    return storage.create_regulation(regulation)


@app.get("/regulations/search", response_model=list[Regulation], dependencies=[Depends(require_api_key)])
def search_regulations(
    q: str = Query(min_length=1, max_length=500),
    on_date: date | None = None,
    limit: int = Query(default=5, ge=1, le=20),
) -> list[Regulation]:
    return storage.search_regulations(q, on_date.isoformat() if on_date else None, limit)


@app.get("/organizations/{organization_id}/dashboard", response_model=DashboardSummary, dependencies=[Depends(require_api_key)])
def read_dashboard(organization_id: str) -> DashboardSummary:
    return storage.dashboard(organization_id)
