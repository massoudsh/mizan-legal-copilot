# Risk Engine

> هستهٔ تحلیلی میزان: پرامپت‌سازی برای LLM + fallback قاعده‌محور وقتی LLM در دسترس نیست/شکست بخورد.

## مسئولیت‌ها
- `analyze_document(document_name, document_text, org_profile) -> RiskAnalysisResult` — نقطهٔ ورود اصلی.
  1. اگر `LLMClient.is_configured()` → `SYSTEM_PROMPT` + `USER_PROMPT_TEMPLATE` را می‌سازد (متن سند تا ۱۲٬۰۰۰ کاراکتر truncate می‌شود)، از LLM JSON می‌گیرد، به `RiskAnalysisResult` تبدیل می‌کند (`analysis_mode="llm"`).
  2. اگر LLM شکست بخورد (استثنا یا JSON نامعتبر) یا کلید نباشد → `_rule_based_fallback` (`analysis_mode="rule_fallback"`).
- `_rule_based_fallback` — روی ۵ الگوی regex از پیش‌تعریف‌شده (`_KEYWORD_RULES`) متن را می‌گردد و findings متناظر را می‌سازد؛ `overall_risk_level` = بالاترین سطح یافته‌شده.

## قواعد کلیدواژه‌ای فعلی (fallback)
| الگو | دسته | سطح |
|---|---|---|
| پیمانکار / قرارداد همکاری / حق‌الزحمه | labor | medium (requires_human_advisor=True) |
| مالیات / ارزش افزوده / فاکتور | tax | medium |
| تأمین اجتماعی / بیمه | social_security | medium |
| فورس ماژور / فسخ / جریمه / خسارت | contractual | high (requires_human_advisor=True) |
| مجوز / ابلاغیه / بخشنامه / دستورالعمل | regulatory | medium |

## وابستگی‌ها
- [[entities/llm-client]] — فراخوانی LLM
- [[entities/schemas]] — `OrgProfile`, `RiskFinding`, `RiskAnalysisResult`, `RiskCategory`, `RiskLevel`
- [[concepts/llm-fallback-pattern]]
- [[concepts/risk-analysis-flow]]

## قراردادها / Edge cases
- متن سند به ۱۲٬۰۰۰ کاراکتر اول truncate می‌شود قبل از ارسال به LLM (سند بلندتر بی‌صدا کوتاه می‌شود — بدون هشدار به کاربر؛ نکتهٔ باز در TASKS.md P3-6).
- خروجی `analysis_mode` (`"llm"`/`"rule_fallback"`) تنها راه فعلی برای تشخیص llm واقعی در برابر fallback در **پاسخ API** است؛ به‌صورت متریک عملیاتی جدا surface نشده (نکتهٔ باز TASKS.md P3-6).
- شکست LLM (خطای HTTP، JSON نامعتبر، هر استثنای دیگر) دیگر بی‌صدا catch نمی‌شود — با `logger.warning(..., exc_info=True)` ساختاریافته لاگ می‌شود، بعد به fallback سوییچ می‌کند.
- **دفاع در برابر prompt injection**: `SYSTEM_PROMPT` صریحاً به مدل می‌گوید متن سند را داده بداند نه دستور؛ متن سند در `USER_PROMPT_TEMPLATE` بین دلیمیترهای `<<<DOCUMENT_START>>>`/`<<<DOCUMENT_END>>>` قرار می‌گیرد.

## منابع کد
- `backend/app/risk_engine.py:45` — `analyze_document`
- `backend/app/risk_engine.py:80` — `_KEYWORD_RULES`
- `backend/app/risk_engine.py:149` — `_rule_based_fallback`
