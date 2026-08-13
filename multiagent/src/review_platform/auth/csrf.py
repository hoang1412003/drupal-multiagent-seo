"""CSRF helpers cho login pre-auth va form trong authenticated session."""
import hashlib
import hmac
import secrets


def issue_login_csrf(signing_key: bytes) -> str:
    nonce = secrets.token_urlsafe(32)
    signature = hmac.new(
        signing_key,
        nonce.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{nonce}.{signature}"


def verify_login_csrf(
    cookie_token: str | None,
    form_token: str | None,
    signing_key: bytes,
) -> bool:
    if not isinstance(cookie_token, str) or not isinstance(form_token, str):
        return False
    try:
        if not hmac.compare_digest(cookie_token, form_token):
            return False
    except TypeError:
        return False
    nonce, separator, supplied_signature = cookie_token.rpartition(".")
    if not separator or not nonce or not supplied_signature:
        return False
    try:
        expected_signature = hmac.new(
            signing_key,
            nonce.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_signature, supplied_signature)
    except (TypeError, UnicodeEncodeError):
        return False


def verify_session_csrf(expected: str, supplied: str | None) -> bool:
    if not isinstance(expected, str) or not isinstance(supplied, str):
        return False
    try:
        return hmac.compare_digest(expected, supplied)
    except TypeError:
        return False
