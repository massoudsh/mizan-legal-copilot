# Schemas (Pydantic Models)

> مدل‌های ورودی/خروجی سرویس تحلیل ریسک.

## مسئولیت‌ها
- `RiskCategory` (Enum): `labor`, `tax`, `social_security`, `contractual`, `regulatory`
- `RiskLevel` (Enum): `low`, `medium`, `high`, `critical`
- `OrgProfile` — پروفایل حداقلی سازمان: `industry`, `employee_count` (≥0), `contractor_ratio_pct` (۰-۱۰۰), `monthly_revenue_toman` (≥0) — همه اختیاری
- `RiskFinding` — یک یافتهٔ ریسک: `category`, `level`, `title`, `explanation`, `evidence` (nullable), `recommended_action`, `requires_human_advisor` (bool, default False)
- `RiskAnalysisResult` — خروجی نهایی: `document_name`, `overall_risk_level`, `summary`, `findings: list[RiskFinding]`, `analysis_mode` (`"llm"` یا `"rule_fallback"`)

## وابستگی‌ها
- استفاده‌شده در [[entities/api-main]] و [[entities/risk-engine]]

## قراردادها / Edge cases
- `analysis_mode` یک `str` آزاد است نه Enum — هیچ enforcement روی مقدار `"llm"`/`"rule_fallback"` در سطح type نیست.

## منابع کد
- `backend/app/schemas.py`
