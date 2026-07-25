"""مدل‌های ورودی/خروجی سرویس تحلیل ریسک میزان."""

from enum import Enum

from pydantic import BaseModel, Field


class RiskCategory(str, Enum):
    LABOR = "labor"  # حقوق کار / رابطه کار
    TAX = "tax"  # مالیاتی
    SOCIAL_SECURITY = "social_security"  # تأمین اجتماعی
    CONTRACTUAL = "contractual"  # قابلیت اجرای بندهای قراردادی
    REGULATORY = "regulatory"  # رگولاتوری / مجوزها / ابلاغیه‌ها


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OrgProfile(BaseModel):
    """پروفایل حداقلی سازمان برای شخصی‌سازی تحلیل (نسخه MVP)."""

    industry: str | None = Field(default=None, description="صنعت/جنس کسب‌وکار")
    employee_count: int | None = Field(default=None, ge=0)
    contractor_ratio_pct: float | None = Field(
        default=None, ge=0, le=100, description="درصد نیروی پیمانکاری/غیرکارمند رسمی"
    )
    monthly_revenue_toman: float | None = Field(default=None, ge=0)


class RiskFinding(BaseModel):
    category: RiskCategory
    level: RiskLevel
    title: str = Field(description="عنوان کوتاه یافته")
    explanation: str = Field(description="توضیح به زبان مدیریتی، نه حقوقی صرف")
    evidence: str | None = Field(default=None, description="نقل‌قول یا اشاره به بخش سند که این ریسک را نشان می‌دهد")
    recommended_action: str = Field(description="گام اصلاحی پیشنهادی")
    requires_human_advisor: bool = Field(
        default=False, description="آیا این مورد باید حتماً توسط مشاور انسانی بررسی شود"
    )


class RiskAnalysisResult(BaseModel):
    document_name: str
    overall_risk_level: RiskLevel
    summary: str = Field(description="جمع‌بندی یک/دو خطی برای مدیرعامل")
    findings: list[RiskFinding]
    analysis_mode: str = Field(description="'llm' یا 'rule_fallback' — منبع تولید تحلیل")
