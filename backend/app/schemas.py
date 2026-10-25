"""Schemas for Mizan's public, tenant-scoped and governance APIs."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class RiskCategory(str, Enum):
    LABOR = "labor"
    TAX = "tax"
    SOCIAL_SECURITY = "social_security"
    CONTRACTUAL = "contractual"
    REGULATORY = "regulatory"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OrgProfile(BaseModel):
    industry: str | None = None
    employee_count: int | None = Field(default=None, ge=0)
    contractor_ratio_pct: float | None = Field(default=None, ge=0, le=100)
    monthly_revenue_toman: float | None = Field(default=None, ge=0)


class OrganizationProfile(OrgProfile):
    organization_id: str
    updated_at: datetime


class OrganizationProfileInput(OrgProfile):
    pass


class OrganizationInput(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class UserInput(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(owner|admin|analyst|viewer)$")


class UserCreated(BaseModel):
    id: int
    organization_id: str
    email: EmailStr
    role: str
    access_token: str


class DemoRequestInput(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    organization: str = Field(min_length=2, max_length=200)
    work_email: EmailStr
    phone: str | None = Field(default=None, max_length=32)
    employee_count: int | None = Field(default=None, ge=1, le=1_000_000)
    message: str | None = Field(default=None, max_length=2000)
    website: str = Field(default="", max_length=0)  # honeypot


class DemoRequest(BaseModel):
    id: int
    created_at: datetime


class RiskFinding(BaseModel):
    category: RiskCategory
    level: RiskLevel
    title: str
    explanation: str
    evidence: str | None = None
    recommended_action: str
    requires_human_advisor: bool = False


class RiskAnalysisResult(BaseModel):
    document_name: str
    overall_risk_level: RiskLevel
    summary: str
    findings: list[RiskFinding]
    analysis_mode: str


class DecisionInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=10000)
    supporting_document: str | None = Field(default=None, max_length=300)
    risk_level: RiskLevel = RiskLevel.MEDIUM


class Decision(DecisionInput):
    id: int
    created_at: datetime


class RegulationInput(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=50000)
    source_url: HttpUrl | None = None
    source_name: str = Field(min_length=2, max_length=200)
    source_version: str = Field(min_length=1, max_length=100)
    trust_score: int = Field(default=50, ge=0, le=100)
    published_on: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class Regulation(RegulationInput):
    id: int
    created_at: datetime


class Alert(BaseModel):
    id: int
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None = None


class RegulatorySourceInput(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    feed_url: HttpUrl


class RegulatorySource(RegulatorySourceInput):
    id: int
    enabled: bool
    last_checked_at: datetime | None = None


class ObligationInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5000)
    due_on: date
    owner_email: EmailStr | None = None
    status: str = Field(default="open", pattern="^(open|in_progress|done|overdue)$")


class Obligation(ObligationInput):
    id: int
    created_at: datetime


class ReviewInput(BaseModel):
    decision_id: int
    reviewer_email: EmailStr
    status: str = Field(default="pending", pattern="^(pending|approved|rejected)$")
    note: str | None = Field(default=None, max_length=5000)


class Review(ReviewInput):
    id: int
    created_at: datetime


class ContractVersionInput(BaseModel):
    contract_key: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=50)
    body: str = Field(min_length=1, max_length=100000)


class ContractDiff(BaseModel):
    contract_key: str
    from_version: str
    to_version: str
    added: list[str]
    removed: list[str]


class AuditExport(BaseModel):
    organization_id: str
    generated_at: datetime
    decisions: list[Decision]
    reviews: list[Review]
    obligations: list[Obligation]


class ConnectorInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    kind: str = Field(pattern="^(hr|finance)$")
    base_url: HttpUrl
    secret_reference: str = Field(min_length=3, max_length=200)


class Connector(ConnectorInput):
    id: int
    enabled: bool
    created_at: datetime


class DashboardSummary(BaseModel):
    organization_id: str
    decision_count: int
    critical_decision_count: int
    risk_distribution: dict[RiskLevel, int]
    recent_decisions: list[Decision]
    unread_alert_count: int
