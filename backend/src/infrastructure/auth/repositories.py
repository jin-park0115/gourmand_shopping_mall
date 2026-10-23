"""회원·인증 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.member import Member, MemberRole
from domain.exceptions import ConflictError
from infrastructure.auth.models import MemberModel

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


def _to_domain(row: MemberModel) -> Member:
    return Member(
        id=row.member_id,
        email=row.email,
        name=row.name,
        phone=row.phone,
        role=MemberRole(row.role),
        password_hash=row.password_hash,
    )
