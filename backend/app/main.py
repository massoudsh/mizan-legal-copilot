"""میزان — MVP سرویس تحلیل ریسک حقوقی/رگولاتوری.

اجرا:
    uvicorn app.main:app --reload --port 8000
"""

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.document_parser import UnsupportedFileTypeError, extract_text
from app.risk_engine import analyze_document
from app.schemas import OrgProfile, RiskAnalysisResult

load_dotenv()

app = FastAPI(
    title="Mizan — Legal & Regulatory Risk Copilot API",
    description="سرویس تحلیل ریسک حقوقی، مالیاتی، تأمین اجتماعی و قراردادی برای سازمان‌های ایرانی",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=RiskAnalysisResult)
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
