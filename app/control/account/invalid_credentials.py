"""Shared handling for upstream invalid-credential failures."""

from typing import TYPE_CHECKING

from app.platform.errors import UpstreamError
from app.platform.logging.logger import logger
from app.platform.runtime.clock import now_ms

from .commands import AccountPatch
from .enums import AccountStatus, FeedbackKind
from .rules import response_is_invalid_account

if TYPE_CHECKING:
    from .repository import AccountRepository


async def mark_account_invalid_credentials(
    repo: "AccountRepository",
    token: str,
    exc: BaseException,
    *,
    source: str,
) -> bool:
    """Mark *token* as invalid when *exc* matches Grok invalid credentials."""
    status = getattr(exc, "status", None)
    body = ""
    if isinstance(exc, UpstreamError):
        body = str(exc.details.get("body", "") or "")
    if not response_is_invalid_account(status, body):
        return False

    record = next(iter(await repo.get_accounts([token])), None)
    reason = "invalid_credentials"
    ts = now_ms()
    ext = record.ext if record is not None else {}

    await repo.patch_accounts(
        [
            AccountPatch(
                token=token,
                status=AccountStatus.EXPIRED,
                last_fail_at=ts,
                last_fail_reason=reason,
                state_reason=reason,
                ext_merge={
                    **ext,
                    "expired_at": ts,
                    "expired_reason": reason,
                },
            )
        ]
    )
    logger.info(
        "account expired from {}: token={}... status={} upstream_status={}",
        source,
        token[:10],
        AccountStatus.EXPIRED,
        status,
    )
    return True


def feedback_kind_for_error(exc: BaseException | None) -> FeedbackKind:
    """Map an upstream exception to the appropriate account feedback kind."""
    if exc is None:
        return FeedbackKind.SERVER_ERROR
    status = getattr(exc, "status", 0)
    body = ""
    if isinstance(exc, UpstreamError):
        body = str(exc.details.get("body", "") or "")
    if response_is_invalid_account(status, body):
        return FeedbackKind.UNAUTHORIZED
    if status == 429:
        return FeedbackKind.RATE_LIMITED
    if status == 401:
        return FeedbackKind.UNAUTHORIZED
    if status == 403:
        return FeedbackKind.FORBIDDEN
    return FeedbackKind.SERVER_ERROR


__all__ = ["mark_account_invalid_credentials", "feedback_kind_for_error"]
