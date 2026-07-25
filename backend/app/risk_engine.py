"""موتور تحلیل ریسک: پرامپت‌سازی برای LLM + fallback قاعده‌محور بدون نیاز به کلید API."""

import re

from app.llm_client import LLMClient
from app.schemas import OrgProfile, RiskAnalysisResult, RiskCategory, RiskFinding, RiskLevel

SYSTEM_PROMPT = """\
تو «میزان» هستی: دستیار تحلیل ریسک‌های حقوقی، مالیاتی، تأمین اجتماعی و قراردادی برای سازمان‌های ایرانی.
سند ارائه‌شده را بر اساس قوانین ایران و رویه‌های اجرایی رایج تحلیل کن، نه فقط متن خام قانون.
خروجی را دقیقاً به‌صورت یک شیء JSON با ساختار زیر برگردان (بدون هیچ متن اضافه):

{
  "overall_risk_level": "low" | "medium" | "high" | "critical",
  "summary": "جمع‌بندی یک تا دو خطی به زبان مدیریتی",
  "findings": [
    {
      "category": "labor" | "tax" | "social_security" | "contractual" | "regulatory",
      "level": "low" | "medium" | "high" | "critical",
      "title": "عنوان کوتاه",
      "explanation": "توضیح روشن به زبان مدیریتی، نه حقوقی صرف",
      "evidence": "نقل‌قول یا اشاره به بخش سند",
      "recommended_action": "گام اصلاحی مشخص",
      "requires_human_advisor": true | false
    }
  ]
}

اگر ریسک یافته‌شده پیچیده یا مبهم است یا می‌تواند پیامد مالی/حقوقی سنگین داشته باشد، requires_human_advisor را true بگذار.
اگر سند هیچ ریسک قابل‌توجهی ندارد، findings را آرایه‌ی خالی برگردان و overall_risk_level را "low" بگذار.
"""

USER_PROMPT_TEMPLATE = """\
### پروفایل سازمان
- صنعت: {industry}
- تعداد پرسنل: {employee_count}
- درصد نیروی پیمانکاری: {contractor_ratio_pct}
- درآمد ماهانه (تومان): {monthly_revenue_toman}

### متن سند («{document_name}»)
{document_text}
"""


def analyze_document(document_name: str, document_text: str, org_profile: OrgProfile) -> RiskAnalysisResult:
    client = LLMClient()

    if client.is_configured():
        try:
            payload = client.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(
                    industry=org_profile.industry or "نامشخص",
                    employee_count=org_profile.employee_count or "نامشخص",
                    contractor_ratio_pct=org_profile.contractor_ratio_pct or "نامشخص",
                    monthly_revenue_toman=org_profile.monthly_revenue_toman or "نامشخص",
                    document_name=document_name,
                    document_text=document_text[:12000],
                ),
            )
            return RiskAnalysisResult(
                document_name=document_name,
                overall_risk_level=payload["overall_risk_level"],
                summary=payload["summary"],
                findings=[RiskFinding(**f) for f in payload.get("findings", [])],
                analysis_mode="llm",
            )
        except Exception:
            # اگر پاسخ LLM ساختار نامعتبر داشت یا فراخوانی شکست خورد، به fallback قاعده‌محور برمی‌گردیم
            pass

    return _rule_based_fallback(document_name, document_text)


# ---------------------------------------------------------------------------
# Fallback قاعده‌محور — برای اجرا/تست MVP بدون نیاز به کلید API.
# جایگزین تحلیل LLM نیست؛ فقط الگوهای کلیدواژه‌ای پرتکرار ریسک را پرچم می‌زند.
# ---------------------------------------------------------------------------

_KEYWORD_RULES: list[tuple[re.Pattern, RiskFinding]] = [
    (
        re.compile(r"پیمانکار|قرارداد\s*همکاری|حق\s*الزحمه"),
        RiskFinding(
            category=RiskCategory.LABOR,
            level=RiskLevel.MEDIUM,
            title="احتمال تلقی رابطه کار به‌جای قرارداد پیمانکاری",
            explanation=(
                "سند حاوی عباراتی نظیر «پیمانکار» یا «قرارداد همکاری» است. اگر ماهیت واقعی رابطه شبیه استخدام "
                "(ساعت کاری ثابت، تبعیت سازمانی) باشد، اداره کار/تأمین اجتماعی می‌تواند آن را رابطه کار تلقی کند."
            ),
            evidence=None,
            recommended_action="بررسی ماهیت واقعی همکاری و در صورت لزوم اصلاح قرارداد یا مستندسازی استقلال طرف مقابل.",
            requires_human_advisor=True,
        ),
    ),
    (
        re.compile(r"مالیات|ارزش\s*افزوده|فاکتور"),
        RiskFinding(
            category=RiskCategory.TAX,
            level=RiskLevel.MEDIUM,
            title="نیاز به بررسی تطابق مالیاتی",
            explanation="سند به موضوعات مالیاتی/فاکتور اشاره دارد که باید با آخرین مقررات مالیاتی سنجیده شود.",
            evidence=None,
            recommended_action="تطبیق بند مالی سند با آخرین بخشنامه‌های سازمان امور مالیاتی.",
            requires_human_advisor=False,
        ),
    ),
    (
        re.compile(r"تأمین\s*اجتماعی|بیمه"),
        RiskFinding(
            category=RiskCategory.SOCIAL_SECURITY,
            level=RiskLevel.MEDIUM,
            title="بررسی الزامات بیمه/تأمین اجتماعی",
            explanation="سند به بیمه/تأمین اجتماعی اشاره دارد؛ لازم است مدل پرداخت مطابق نصاب‌های مصوب باشد.",
            evidence=None,
            recommended_action="راستی‌آزمایی مدل پرداخت حق بیمه با آخرین دستورالعمل سازمان تأمین اجتماعی.",
            requires_human_advisor=False,
        ),
    ),
    (
        re.compile(r"فورس\s*ماژور|فسخ|جریمه|خسارت"),
        RiskFinding(
            category=RiskCategory.CONTRACTUAL,
            level=RiskLevel.HIGH,
            title="بند فسخ/جریمه نیازمند بررسی قابلیت اجرا",
            explanation="بندهای فسخ، جریمه یا خسارت باید از نظر قابلیت اجرا در نظام حقوقی ایران دقیق بررسی شوند.",
            evidence=None,
            recommended_action="ارجاع بند به مشاور حقوقی برای تأیید قابلیت اجرا و شفاف‌سازی شرایط فسخ.",
            requires_human_advisor=True,
        ),
    ),
    (
        re.compile(r"مجوز|ابلاغیه|بخشنامه|دستورالعمل"),
        RiskFinding(
            category=RiskCategory.REGULATORY,
            level=RiskLevel.MEDIUM,
            title="وابستگی به مجوز/ابلاغیه رگولاتوری",
            explanation="سند به مجوز یا ابلاغیه‌ای اشاره دارد که باید از نظر تاریخ اعتبار و آخرین نسخه بررسی شود.",
            evidence=None,
            recommended_action="بررسی تاریخ آخرین به‌روزرسانی ابلاغیه/مجوز مرتبط پیش از اتکا به آن.",
            requires_human_advisor=False,
        ),
    ),
]

_LEVEL_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}


def _rule_based_fallback(document_name: str, document_text: str) -> RiskAnalysisResult:
    findings = [finding for pattern, finding in _KEYWORD_RULES if pattern.search(document_text)]

    overall = max((f.level for f in findings), key=lambda lvl: _LEVEL_ORDER[lvl], default=RiskLevel.LOW)

    summary = (
        f"{len(findings)} ریسک بالقوه بر اساس تحلیل کلیدواژه‌ای شناسایی شد. "
        "این تحلیل حالت fallback است (بدون LLM) — برای دقت بالاتر LLM_API_KEY را تنظیم کنید."
        if findings
        else "بر اساس تحلیل کلیدواژه‌ای اولیه، ریسک قابل‌توجهی یافت نشد. توجه: این حالت fallback است."
    )

    return RiskAnalysisResult(
        document_name=document_name,
        overall_risk_level=overall,
        summary=summary,
        findings=findings,
        analysis_mode="rule_fallback",
    )
