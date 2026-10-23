"""비밀번호 해싱(argon2) · access token(JWT) 발급 · 검증."""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from core.config import Settings
from domain.auth.member import Member, MemberRole, TokenClaims
from domain.exceptions import AuthenticationError

_hasher = PasswordHash.recommended()  # argon2 (시드 스크립트와 같은 방식)

# 없는 이메일로 로그인해도 해시 비교 시간을 들여서, 응답 시간으로 가입 여부를 알 수 없게 해요
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    try:
        return _hasher.verify(password, password_hash)
    except Exception:  # 형식이 깨진 해시(예: 테스트용 "x")는 틀린 비밀번호로 봐요
        return False


def create_access_token(member: Member, settings: Settings, *, now: datetime | None = None) -> tuple[str, int]:
    """(토큰, 유효 시간 초)를 돌려줘요."""
    now = now or datetime.now(UTC)
    expires_in = settings.access_token_expire_minutes * 60
    payload = {
        "sub": str(member.id),  # JWT 표준상 sub 는 문자열이에요
        "role": member.role.value,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), expires_in


def decode_access_token(token: str, settings: Settings) -> TokenClaims:
    """서명 · 만료를 검사하고 값을 꺼내요. 문제가 있으면 모두 401 이에요."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "role", "jti", "exp"]},
        )
        return TokenClaims(
            member_id=int(payload["sub"]),
            role=MemberRole(payload["role"]),
            jti=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("로그인이 만료됐어요. 다시 로그인해 주세요.") from None
    except (jwt.InvalidTokenError, ValueError):
        raise AuthenticationError("로그인 정보가 올바르지 않아요. 다시 로그인해 주세요.") from None
