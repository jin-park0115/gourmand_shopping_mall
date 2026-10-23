"""회원·인증 요청·응답 Pydantic 스키마."""
from pydantic import BaseModel, EmailStr, Field

from domain.auth.member import NAME_MAX_LENGTH, PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, Member
from presentation.schemas import CamelModel


class SignupIn(CamelModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    phone: str | None = Field(None, pattern=r"^[0-9-]{9,20}$")


class MemberOut(CamelModel):
    id: int
    email: str
    name: str
    phone: str | None
    role: str

    @classmethod
    def of(cls, member: Member) -> "MemberOut":
        return cls(id=member.id, email=member.email, name=member.name, phone=member.phone, role=member.role.value)


class TokenOut(BaseModel):
    """OAuth2 표준 응답이라 camelCase 가 아니라 snake_case 예요 (Swagger Authorize 버튼도 이 모양을 읽어요)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 초
