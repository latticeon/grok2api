"""Token display helpers for logs."""


def format_token_for_log(token: str, visible: int = 8) -> str:
    """Return a stable masked token string using only trailing characters."""
    value = str(token or "")
    if not value:
        return "<empty>"
    if value.startswith("sso="):
        value = value[4:]
    if len(value) <= visible:
        return value
    return f"...{value[-visible:]}"


__all__ = ["format_token_for_log"]
