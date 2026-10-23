"""SCRUM-18: 가입 규칙 · 비밀번호 해싱 · JWT (DB 없이)."""
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from core.config import Settings
from domain.auth.member import Member, MemberRole, normalize_email, validate_name, validate_password
from domain.exceptions import AuthenticationError, InvalidValueError
from infrastructure.auth.security import create_access_token, decode_access_token, hash_password, verify_password

SECRET = "test-secret-key-that-is-at-least-32-bytes"
SETTINGS = Settings(_env_file=None, jwt_secret_key=SECRET, access_token_expire_minutes=60)
MEMBER = Member(id=7, email="a@test.com", name="김구르", phone=None, role=MemberRole.ADMIN, password_hash="h")


def test_email_is_lowercased_and_trimmed() -> None:
    assert normalize_email("  Kim@Gourmand.COM ") == "kim@gourmand.com"


@pytest.mark.parametrize("password", ["1234567", "x" * 65])
def test_password_length_rule(password: str) -> None:
    with pytest.raises(InvalidValueError):
        validate_password(password)


def test_password_length_bounds_pass() -> None:
    validate_password("x" * 8)
    validate_password("x" * 64)


def test_blank_name_is_rejected() -> None:
    with pytest.raises(InvalidValueError):
        validate_name("   ")
    assert validate_name(" 김구르 ") == "김구르"


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("secret-123")
    assert hashed != "secret-123"
    assert verify_password("secret-123", hashed)
    assert not verify_password("wrong-pass", hashed)


def test_verify_against_missing_or_broken_hash_is_false() -> None:
    assert not verify_password("secret-123", None)
    assert not verify_password("secret-123", "x")


def test_token_has_sub_role_jti_exp() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    token, expires_in = create_access_token(MEMBER, SETTINGS, now=now)
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])

    assert expires_in == 3600
    assert payload["sub"] == "7"
    assert payload["role"] == "admin"
    assert len(payload["jti"]) == 32
    assert payload["exp"] == int((now + timedelta(hours=1)).timestamp())


def test_each_token_gets_new_jti() -> None:
    first = decode_access_token(create_access_token(MEMBER, SETTINGS)[0], SETTINGS)
    second = decode_access_token(create_access_token(MEMBER, SETTINGS)[0], SETTINGS)
    assert first.jti != second.jti
    assert (first.member_id, first.role) == (7, MemberRole.ADMIN)


def test_expired_token_is_401() -> None:
    token, _ = create_access_token(MEMBER, SETTINGS, now=datetime.now(UTC) - timedelta(hours=2))
    with pytest.raises(AuthenticationError, match="만료"):
        decode_access_token(token, SETTINGS)


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        create_access_token(MEMBER, Settings(_env_file=None, jwt_secret_key="other-secret-key-that-is-at-least-32-bytes"))[0],  # 다른 키로 서명
        jwt.encode({"sub": "7", "exp": datetime.now(UTC) + timedelta(hours=1)}, SECRET),  # role · jti 없음
    ],
)
def test_invalid_token_is_401(token: str) -> None:
    with pytest.raises(AuthenticationError):
        decode_access_token(token, SETTINGS)
