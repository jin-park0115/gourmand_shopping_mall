"""회원 도메인 객체와 가입 규칙 (순수 파이썬).

규칙: 이메일은 소문자로 저장, 비밀번호 8~64자, 이름 1~50자.
이메일 형식(@ · 도메인) 검사는 요청 스키마(EmailStr)가 먼저 해요.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from domain.exceptions import InvalidValueError

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64  # 해싱 비용이 큰 아주 긴 입력을 막아요
NAME_MAX_LENGTH = 50


class MemberRole(StrEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"


@dataclass(frozen=True)
class Member:
    id: int
    email: str
    name: str
    phone: str | None
    role: MemberRole
    password_hash: str = field(repr=False)  # 로그에 찍히지 않게

    @property
    def is_admin(self) -> bool:
        return self.role is MemberRole.ADMIN


@dataclass(frozen=True)
class TokenClaims:
    """access token 에 담긴 값 (sub · role · jti · exp). SCRUM-19 로그아웃 · 권한 확인에서 써요."""

    member_id: int
    role: MemberRole
    jti: str  # 토큰마다 다른 id. 로그아웃하면 이 값을 블랙리스트에 넣어요
    expires_at: datetime


def normalize_email(email: str) -> str:
    """대소문자만 다른 이메일로 두 번 가입하지 못하게 소문자로 맞춰요."""
    return email.strip().lower()


def validate_password(password: str) -> None:
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise InvalidValueError(f"비밀번호는 {PASSWORD_MIN_LENGTH}~{PASSWORD_MAX_LENGTH}자여야 해요.")


def validate_name(name: str) -> str:
    name = name.strip()
    if not 1 <= len(name) <= NAME_MAX_LENGTH:
        raise InvalidValueError(f"이름은 1~{NAME_MAX_LENGTH}자여야 해요.")
    return name
