"""회원·인증 ORM 모델."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class MemberModel(Base):
    __tablename__ = "member"

    member_id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))
    # ERD 에는 없지만 require_admin(SCRUM 관리자 권한)에 필요 — "customer" | "admin"
    role: Mapped[str] = mapped_column(String(20), default="customer", server_default="customer")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    addresses: Mapped[list["AddressModel"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )


class AddressModel(Base):
    __tablename__ = "address"

    address_id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("member.member_id", ondelete="CASCADE"), index=True)
    recipient: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))
    zipcode: Mapped[str] = mapped_column(String(10))
    address1: Mapped[str] = mapped_column(String(200))
    address2: Mapped[str | None] = mapped_column(String(200))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    member: Mapped[MemberModel] = relationship(back_populates="addresses")


class TokenBlacklistModel(Base):
    """로그아웃한 access token 의 jti (SCRUM-19). 만료된 줄은 다음 로그아웃 때 지워요."""

    __tablename__ = "token_blacklist"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
