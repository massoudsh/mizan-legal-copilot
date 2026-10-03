"""محدودکننده‌ی نرخ درخواست (in-memory) برای endpoint های سنگین.

این ماژول یک محدودکننده‌ی پنجره‌ی لغزان (sliding window) ساده و بدون وابستگی اضافه فراهم می‌کند
تا از endpoint های پرهزینه مثل `/analyze` در برابر فراخوانی پشت‌سرهم محافظت شود.

محدودیت‌ها با متغیرهای محیطی قابل تنظیم‌اند:
    RATE_LIMIT_REQUESTS        تعداد مجاز درخواست در هر پنجره (پیش‌فرض: 10)
    RATE_LIMIT_WINDOW_SECONDS  طول پنجره به ثانیه (پیش‌فرض: 60)

توجه: وضعیت شمارنده‌ها در حافظه‌ی همین پروسه نگه داشته می‌شود. برای استقرار چند-پروسه‌ای یا
چند-نمونه‌ای (horizontal scale) باید به یک فروشگاه مشترک مثل Redis منتقل شود.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request, status


def _env_positive_int(name: str, default: int) -> int:
    """خواندن یک عدد صحیح مثبت از محیط؛ در صورت نبود/نامعتبر بودن، مقدار پیش‌فرض."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


class SlidingWindowRateLimiter:
    """محدودکننده‌ی نرخ پنجره‌ی لغزان، کلید‌محور و امن برای استفاده‌ی همزمان.

    هر کلید (مثلاً IP کلاینت) یک صف از زمان درخواست‌ها دارد؛ درخواست‌های قدیمی‌تر از پنجره
    حذف می‌شوند و اگر تعداد درخواست‌های داخل پنجره به سقف برسد، درخواست رد می‌شود.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests باید مثبت باشد.")
        if window_seconds <= 0:
            raise ValueError("window_seconds باید مثبت باشد.")

        self.max_requests = max_requests
        self.window_seconds = float(window_seconds)

        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = 0.0

    def check(self, key: str, now: float | None = None) -> tuple[bool, float]:
        """ثبت یک درخواست برای `key`.

        خروجی: (مجاز بودن، ثانیه‌های باقی‌مانده تا تلاش بعدی).
        برای درخواست مجاز، مقدار دوم صفر است.
        """
        current = time.monotonic() if now is None else now

        with self._lock:
            self._cleanup(current)

            bucket = self._hits.setdefault(key, deque())
            cutoff = current - self.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = bucket[0] + self.window_seconds - current
                return False, max(retry_after, 0.0)

            bucket.append(current)
            return True, 0.0

    def _cleanup(self, now: float) -> None:
        """حذف کلیدهای بی‌استفاده تا حافظه با گذر زمان رشد نکند."""
        if now - self._last_cleanup < self.window_seconds:
            return
        self._last_cleanup = now

        cutoff = now - self.window_seconds
        stale = [key for key, bucket in self._hits.items() if not bucket or bucket[-1] <= cutoff]
        for key in stale:
            del self._hits[key]


_limiter = SlidingWindowRateLimiter(
    max_requests=_env_positive_int("RATE_LIMIT_REQUESTS", 10),
    window_seconds=_env_positive_int("RATE_LIMIT_WINDOW_SECONDS", 60),
)


def _client_key(request: Request) -> str:
    """کلید محدودسازی: IP کلاینت (با احترام به هدر پراکسی در صورت وجود)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_rate_limit(request: Request) -> None:
    """وابستگی FastAPI برای اعمال محدودیت نرخ روی یک route.

    در صورت عبور از سقف، پاسخ 429 همراه با هدر `Retry-After` برگردانده می‌شود.
    """
    allowed, retry_after = _limiter.check(_client_key(request))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="تعداد درخواست‌ها بیش از حد مجاز است. لطفاً کمی بعد دوباره تلاش کنید.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
