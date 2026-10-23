"""회원·인증 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.member import Member, MemberRole
from domain.exceptions import ConflictError
from infrastructure.auth.models import MemberModel, TokenBlacklistModel

DUPLICATE_EMAIL_MESSAGE = "이미 가입된 이메일이에요."


class MemberRepository:
    """회원 조회 · 저장. commit 은 응용 서비스가 해요."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, member_id: int) -> Member | None:
        row = await self.session.get(MemberModel, member_id)
        return _to_domain(row) if row else None

    async def get_by_email(self, email: str) -> Member | None:
        row = await self.session.scalar(select(MemberModel).where(MemberModel.email == email))
        return _to_domain(row) if row else None

    async def add(self, *, email: str, password_hash: str, name: str, phone: str | None) -> Member:
        row = MemberModel(email=email, password_hash=password_hash, name=name, phone=phone, role=MemberRole.CUSTOMER)
        self.session.add(row)
        try:
            await self.session.flush()
        except IntegrityError:
            # 같은 이메일로 거의 동시에 가입하면 미리 확인을 통과해도 UNIQUE 제약에 걸려요
            # (세션 rollback 은 요청이 끝날 때 get_session 이 세션을 닫으면서 해요)
            raise ConflictError(DUPLICATE_EMAIL_MESSAGE) from None
        return _to_domain(row)


class TokenBlacklistRepository:
    """로그아웃한 토큰의 jti 목록. commit 은 응용 서비스가 해요."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, jti: str, expires_at: datetime) -> None:
        # 같은 토큰으로 두 번 로그아웃해도 오류 없이 넘어가요
        await self.session.execute(
            insert(TokenBlacklistModel).values(jti=jti, expires_at=expires_at).on_conflict_do_nothing()
        )

    async def contains(self, jti: str) -> bool:
        return await self.session.get(TokenBlacklistModel, jti) is not None

    async def purge_expired(self, now: datetime) -> None:
        """이미 만료된 토큰은 서명 검사에서 막히니 목록에 둘 필요가 없어요."""
        await self.session.execute(delete(TokenBlacklistModel).where(TokenBlacklistModel.expires_at < now))


def _to_domain(row: MemberModel) -> Member:
    return Member(
        id=row.member_id,
        email=row.email,
        name=row.name,
        phone=row.phone,
        role=MemberRole(row.role),
        password_hash=row.password_hash,
    )
