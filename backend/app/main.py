"""میزان — MVP سرویس تحلیل ریسک حقوقی/رگولاتوری.

اجرا:
    uvicorn app.main:app --reload --port 8000
"""

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.document_parser import UnsupportedFileTypeError, extract_text
from app.risk_engine import analyze_document
from app.schemas import OrgProfile, RiskAnalysisResult

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

app = FastAPI(
    title="Mizan — Legal & Regulatory Risk Copilot API",
    description="سرویس تحلیل ریسک حقوقی، مالیاتی، تأمین اجتماعی و قراردادی برای سازمان‌های ایرانی",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
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


@app.post("/analyze", response_model=RiskAnalysisResult, dependencies=[Depends(require_api_key)])
async def analyze(
    file: UploadFile = File(..., description="سند/قرارداد (pdf, docx, txt, md)"),
    industry: str | None = Form(default=None),
    employee_count: int | None = Form(default=None),
    contractor_ratio_pct: float | None = Form(default=None),
    monthly_revenue_toman: float | None = Form(default=None),
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
        raise HTTPException(status_code=422, detail="متنی از فایل استخراج نشد (احتمالاً اسکن‌شده بدون OCR است).")

    org_profile = OrgProfile(
        industry=industry,
        employee_count=employee_count,
        contractor_ratio_pct=contractor_ratio_pct,
        monthly_revenue_toman=monthly_revenue_toman,
    )

    return analyze_document(document_name=file.filename or "document", document_text=text, org_profile=org_profile)
