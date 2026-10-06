"""مدل‌های ورودی/خروجی سرویس تحلیل ریسک میزان."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


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
    industry: str | None = Field(default=None, description="صنعت/جنس کسب‌وکار")
    employee_count: int | None = Field(default=None, ge=0)
    contractor_ratio_pct: float | None = Field(default=None, ge=0, le=100)
    monthly_revenue_toman: float | None = Field(default=None, ge=0)


class OrganizationProfile(OrgProfile):
    organization_id: str = Field(min_length=1, max_length=128)
    updated_at: datetime


class OrganizationProfileInput(OrgProfile):
    organization_id: str = Field(min_length=1, max_length=128)


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
    organization_id: str = Field(min_length=1, max_length=128)
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
    source_url: str | None = Field(default=None, max_length=2000)
    published_on: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class Regulation(RegulationInput):
    id: int
    created_at: datetime


class DashboardSummary(BaseModel):
    organization_id: str
    decision_count: int
    critical_decision_count: int
    risk_distribution: dict[RiskLevel, int]
    recent_decisions: list[Decision]
