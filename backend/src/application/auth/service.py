"""회원·인증 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from domain.auth.member import Member, normalize_email, validate_name, validate_password
from domain.exceptions import AuthenticationError, ConflictError
from infrastructure.auth.repositories import DUPLICATE_EMAIL_MESSAGE, MemberRepository
from infrastructure.auth.security import create_access_token, hash_password, verify_password

LOGIN_FAILED_MESSAGE = "이메일 또는 비밀번호가 올바르지 않아요."


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings
        self.members = MemberRepository(session)

    async def signup(self, *, email: str, password: str, name: str, phone: str | None) -> Member:
        email = normalize_email(email)
        validate_password(password)
        name = validate_name(name)
        if await self.members.get_by_email(email):
            raise ConflictError(DUPLICATE_EMAIL_MESSAGE)
        member = await self.members.add(email=email, password_hash=hash_password(password), name=name, phone=phone)
        await self.session.commit()
        return member

    async def login(self, *, email: str, password: str) -> tuple[str, int]:
        """(access token, 유효 시간 초). 이메일이 없든 비밀번호가 틀리든 같은 메시지로 401 이에요."""
        member = await self.members.get_by_email(normalize_email(email))
        if not verify_password(password, member.password_hash if member else None):
            raise AuthenticationError(LOGIN_FAILED_MESSAGE)
        return create_access_token(member, self.settings)
