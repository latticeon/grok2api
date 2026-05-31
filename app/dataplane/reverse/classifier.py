"""Reverse pipeline result classifier.

Maps upstream HTTP status codes and response bodies to a ResultCategory.
"""

from typing import Any

from app.control.account.rules import response_is_invalid_account

from .types import ResultCategory


def classify_result(
    status_code: int,
    body: str = "",
    *,
    payload: Any = None,
) -> ResultCategory:
    """Classify an upstream response into a ResultCategory.

    ``body`` is the raw response body (or first ~400 chars for error responses).
    ``payload`` is the parsed JSON, if available.
    """
    if status_code == 200:
        return ResultCategory.SUCCESS

    if status_code == 429:
        return ResultCategory.RATE_LIMITED

    if status_code == 401:
        return ResultCategory.AUTH_FAILURE

    if response_is_invalid_account(status_code, body):
        return ResultCategory.AUTH_FAILURE

    if status_code == 403:
        # Check if the body indicates a Cloudflare challenge.
        if body and ("cf-challenge" in body.lower() or "cloudflare" in body.lower()):
            return ResultCategory.FORBIDDEN
        # Generic 403 (suspension, WAF, etc.) — not a credential issue.
        return ResultCategory.FORBIDDEN

    if status_code == 404:
        return ResultCategory.NOT_FOUND

    if status_code >= 500:
        return ResultCategory.UPSTREAM_5XX

    return ResultCategory.UNKNOWN


__all__ = ["classify_result"]
