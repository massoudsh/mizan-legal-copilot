"""Mizan API: public demo requests and tenant-isolated risk operations."""

import os
from contextlib import asynccontextmanager
from datetime import date
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import storage
from app.auth import Principal, Role, new_token, require_role, token_digest
from app.document_parser import UnsupportedFileTypeError, extract_text
from app.rate_limit import enforce_rate_limit
from app.risk_engine import analyze_document
from app.observability import configure_telemetry
from app.crypto import _fernet
from app.schemas import Connector, ConnectorInput, ContractDiff, ContractVersionInput, DashboardSummary, Decision, DecisionInput, DemoRequest, DemoRequestInput, OrganizationInput, OrganizationProfile, OrganizationProfileInput, Obligation, ObligationInput, Regulation, RegulationInput, RegulatorySource, RegulatorySourceInput, Review, ReviewInput, RiskAnalysisResult, UserCreated, UserInput

load_dotenv()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_KEY = os.getenv("MIZAN_API_KEY")
MAX_UPLOAD_BYTES = int(os.getenv("MIZAN_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
if ENVIRONMENT == "production" and not API_KEY:
    raise RuntimeError("MIZAN_API_KEY must be set in production.")
origins = os.getenv("CORS_ORIGINS", "")
if ENVIRONMENT == "production" and not origins:
    raise RuntimeError("CORS_ORIGINS must be set in production.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _fernet()
    storage.initialize_database()
    yield


app = FastAPI(title="Mizan API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins.split(",") if x.strip()] or ["http://localhost:3000"], allow_credentials=False, allow_methods=["GET", "POST", "PUT"], allow_headers=["Content-Type", "Authorization", "X-API-Key"])
configure_telemetry(app)


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/analyze":
        try:
            if int(request.headers.get("content-length", "0")) > MAX_UPLOAD_BYTES:
                return JSONResponse(status_code=413, content={"detail": "حجم فایل بیش از حد مجاز است."})
        except ValueError:
            pass
    return await call_next(request)


async def require_platform_key(x_api_key: str | None = Header(default=None)) -> None:
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="کلید مدیریتی نامعتبر است.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/demo-requests", response_model=DemoRequest, status_code=201, dependencies=[Depends(enforce_rate_limit)])
def request_demo(value: DemoRequestInput) -> DemoRequest:
    if value.website:
        raise HTTPException(status_code=400, detail="درخواست نامعتبر است.")
    return storage.create_demo_request(value)


@app.post("/admin/organizations", dependencies=[Depends(require_platform_key)])
def create_organization(value: OrganizationInput) -> dict:
    organization_id = str(uuid4())
    storage.create_organization(organization_id, value.name)
    return {"organization_id": organization_id}


@app.post("/admin/organizations/{organization_id}/users", response_model=UserCreated, status_code=201, dependencies=[Depends(require_platform_key)])
def create_user(organization_id: str, value: UserInput) -> UserCreated:
    token = new_token()
    user_id = storage.create_user(organization_id, str(value.email), value.role, token_digest(token))
    return UserCreated(id=user_id, organization_id=organization_id, email=value.email, role=value.role, access_token=token)


@app.post("/analyze", response_model=RiskAnalysisResult, dependencies=[Depends(enforce_rate_limit)])
async def analyze(file: UploadFile = File(...), principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST))) -> RiskAnalysisResult:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="فایل آپلودشده خالی است.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="حجم فایل بیش از حد مجاز است.")
    try:
        text = extract_text(file.filename or "document", content)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not text.strip():
        raise HTTPException(status_code=422, detail="متنی استخراج نشد؛ برای اسکن، OCR را روی سرور نصب کنید.")
    profile = storage.get_profile(principal) or OrganizationProfile(organization_id=principal.organization_id, updated_at=date.today())
    regulations = storage.search_regulations(text[:2000], date.today().isoformat())
    return analyze_document(file.filename or "document", text, profile, regulations)


@app.put("/profile", response_model=OrganizationProfile)
def upsert_profile(value: OrganizationProfileInput, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN))) -> OrganizationProfile:
    return storage.save_profile(principal, value)


@app.get("/profile", response_model=OrganizationProfile)
def read_profile(principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST, Role.VIEWER))) -> OrganizationProfile:
    profile = storage.get_profile(principal)
    if not profile:
        raise HTTPException(status_code=404, detail="پروفایل سازمان یافت نشد.")
    return profile


@app.post("/decisions", response_model=Decision, status_code=201)
def add_decision(value: DecisionInput, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST))) -> Decision:
    return storage.create_decision(principal, value)


@app.get("/decisions", response_model=list[Decision])
def read_decisions(limit: int = Query(50, ge=1, le=200), principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST, Role.VIEWER))) -> list[Decision]:
    return storage.list_decisions(principal, limit)


@app.post("/obligations", response_model=Obligation, status_code=201)
def add_obligation(value: ObligationInput, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST))) -> Obligation:
    return storage.create_obligation(principal, value)


@app.get("/obligations", response_model=list[Obligation])
def obligations(status: str | None = Query(default=None), principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST, Role.VIEWER))) -> list[Obligation]:
    return storage.list_obligations(principal, status)


@app.post("/reviews", response_model=Review, status_code=201)
def add_review(value: ReviewInput, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST))) -> Review:
    return storage.create_review(principal, value)


@app.get("/reviews", response_model=list[Review])
def reviews(decision_id: int | None = None, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST, Role.VIEWER))) -> list[Review]:
    return storage.list_reviews(principal, decision_id)


@app.post("/contract-versions", status_code=201)
def add_contract_version(value: ContractVersionInput, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST))) -> dict:
    storage.save_contract_version(principal, value)
    return {"status": "stored"}


@app.get("/contract-diff", response_model=ContractDiff)
def contract_diff(contract_key: str, from_version: str, to_version: str, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST, Role.VIEWER))) -> ContractDiff:
    try:
        return storage.diff_contract_versions(principal, contract_key, from_version, to_version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/audit-export")
def audit_export(principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST, Role.VIEWER))):
    return storage.audit_export(principal)


@app.post("/regulations", response_model=Regulation, status_code=201)
def ingest_regulation(value: RegulationInput, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN))) -> Regulation:
    regulation, changed = storage.create_regulation(value)
    if changed:
        storage.create_alert_for_all("نسخهٔ جدید مقرره", f"{value.title} با نسخهٔ {value.source_version} ثبت شد.")
    return regulation


@app.get("/regulations/search", response_model=list[Regulation])
def regulations(q: str = Query(min_length=1, max_length=500), on_date: date | None = None, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST, Role.VIEWER))) -> list[Regulation]:
    return storage.search_regulations(q, str(on_date or date.today()))


@app.post("/regulatory-sources", response_model=RegulatorySource, status_code=201)
def add_regulatory_source(value: RegulatorySourceInput, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN))) -> RegulatorySource:
    return storage.create_regulatory_source(value)


@app.get("/regulatory-sources", response_model=list[RegulatorySource])
def regulatory_sources(principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN))) -> list[RegulatorySource]:
    return storage.list_regulatory_sources()


@app.post("/connectors", response_model=Connector, status_code=201)
def add_connector(value: ConnectorInput, principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN))) -> Connector:
    return storage.create_connector(principal, value)


@app.get("/connectors", response_model=list[Connector])
def connectors(principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN))) -> list[Connector]:
    return storage.list_connectors(principal)


@app.get("/dashboard", response_model=DashboardSummary)
def dashboard(principal: Principal = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST, Role.VIEWER))) -> DashboardSummary:
    decisions, distribution, unread = storage.dashboard(principal)
    return DashboardSummary(organization_id=principal.organization_id, decision_count=len(decisions), critical_decision_count=distribution.get("critical", 0), risk_distribution=distribution, recent_decisions=decisions[:10], unread_alert_count=unread)
