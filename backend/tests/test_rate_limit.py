"""تست‌های محدودکننده‌ی نرخ درخواست (بدون نیاز به سرور یا وابستگی خارجی)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.rate_limit import SlidingWindowRateLimiter


def test_allows_requests_up_to_limit():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)

    for i in range(3):
        allowed, retry_after = limiter.check("client-a", now=100.0 + i)
        assert allowed is True, f"درخواست {i + 1} باید مجاز باشد"
        assert retry_after == 0.0


def test_blocks_request_over_limit_and_reports_retry_after():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)

    limiter.check("client-a", now=100.0)
    limiter.check("client-a", now=101.0)

    allowed, retry_after = limiter.check("client-a", now=102.0)

    assert allowed is False
    # قدیمی‌ترین درخواست در t=100 بوده و پنجره در t=160 بسته می‌شود.
    assert retry_after == pytest.approx(58.0)


def test_window_slides_and_frees_capacity():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=10)

    assert limiter.check("client-a", now=0.0)[0] is True
    assert limiter.check("client-a", now=5.0)[0] is False
    # در t=10 درخواست اول از پنجره خارج شده است.
    assert limiter.check("client-a", now=10.0)[0] is True


def test_keys_are_isolated():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)

    assert limiter.check("client-a", now=0.0)[0] is True
    assert limiter.check("client-b", now=0.0)[0] is True
    assert limiter.check("client-a", now=1.0)[0] is False


def test_stale_keys_are_cleaned_up():
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=10)

    limiter.check("client-a", now=0.0)
    assert "client-a" in limiter._hits

    # پس از گذشت بیش از یک پنجره، پاک‌سازی باید کلید بی‌استفاده را حذف کند.
    limiter.check("client-b", now=100.0)

    assert "client-a" not in limiter._hits
    assert "client-b" in limiter._hits


def test_rejects_non_positive_configuration():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_requests=0, window_seconds=60)

    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_requests=10, window_seconds=0)
