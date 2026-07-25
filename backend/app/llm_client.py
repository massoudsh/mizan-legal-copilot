"""کلاینت سبک و قابل‌تعویض برای فراخوانی LLM (سازگار با OpenAI Chat Completions API).

اگر LLM_API_KEY تنظیم نشده باشد، is_configured() False برمی‌گرداند و موتور ریسک
باید به حالت fallback قاعده‌محور سوییچ کند — این طراحی MVP را بدون نیاز به کلید
API قابل اجرا و تست می‌کند.
"""

import json
import os

import requests

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
REQUEST_TIMEOUT_SECONDS = 60


class LLMClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.base_url = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.model = os.getenv("LLM_MODEL", DEFAULT_MODEL)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        """یک درخواست chat completion با پاسخ اجباراً JSON ارسال می‌کند."""

        if not self.is_configured():
            raise RuntimeError("LLM_API_KEY تنظیم نشده است.")

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
