# LLM Client

> کلاینت سبک و قابل‌تعویض برای فراخوانی هر endpoint سازگار با OpenAI Chat Completions.

## مسئولیت‌ها
- `LLMClient.__init__` — کلید/base_url/model را از env می‌خواند.
- `is_configured() -> bool` — آیا `LLM_API_KEY` ست شده.
- `complete_json(system_prompt, user_prompt) -> dict` — درخواست chat completion با `response_format=json_object`، پارس پاسخ به dict.

## Environment Variables
| متغیر | پیش‌فرض |
|---|---|
| `LLM_API_KEY` | (خالی — یعنی `is_configured()` False) |
| `LLM_BASE_URL` | `https://api.openai.com/v1` |
| `LLM_MODEL` | `gpt-4o-mini` |

## وابستگی‌ها
- استفاده‌شده توسط [[entities/risk-engine]]
- [[concepts/llm-fallback-pattern]] — چرا این کلاینت اختیاری طراحی شده

## قراردادها / Edge cases
- Timeout ثابت ۶۰ ثانیه (`REQUEST_TIMEOUT_SECONDS`).
- خطای HTTP → `response.raise_for_status()` exception بالا می‌رود؛ caller (`risk_engine.analyze_document`) آن را می‌گیرد و به fallback سوییچ می‌کند.
- هیچ retry/backoff ندارد.

## منابع کد
- `backend/app/llm_client.py:18` — کلاس `LLMClient`
