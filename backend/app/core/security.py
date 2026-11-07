"""密码哈希与 JWT：密码使用随机盐 PBKDF2-SHA256，绝不明文入库。"""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.logging import get_logger

logger = get_logger(__name__)
_temporary_development_secret = secrets.token_urlsafe(48)


def hash_password(password: str) -> str:
    iterations = settings.password_hash_iterations
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${iterations}${encode(salt)}${encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        salt = decode(salt_text)
        expected = decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations_text))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _jwt_secret() -> str:
    if settings.jwt_secret_key:
        return settings.jwt_secret_key
    if settings.app_env == "production":
        raise RuntimeError("生产环境必须配置 JWT_SECRET_KEY")
    return _temporary_development_secret


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    expires_in = settings.jwt_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=settings.jwt_algorithm), expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError() from exc