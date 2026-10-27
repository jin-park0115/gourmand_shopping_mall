"""회원·인증 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from domain.auth.login_guard import LoginGuard
from domain.auth.member import CurrentUser, Member, normalize_email, validate_name, validate_password
from domain.exceptions import AuthenticationError, ConflictError
from infrastructure.auth.repositories import DUPLICATE_EMAIL_MESSAGE, MemberRepository, TokenBlacklistRepository
from infrastructure.auth.security import create_access_token, decode_access_token, hash_password, verify_password

LOGIN_FAILED_MESSAGE = "이메일 또는 비밀번호가 올바르지 않아요."
LOGGED_OUT_MESSAGE = "로그아웃된 토큰이에요. 다시 로그인해 주세요."

# 같은 이메일 연속 실패 잠금 (서버 한 대 기준, 서버 메모리). 테스트는 conftest 에서 매번 reset
login_guard = LoginGuard()


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings
        self.members = MemberRepository(session)
        self.blacklist = TokenBlacklistRepository(session)

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
        email = normalize_email(email)
        login_guard.check(email)  # 연속으로 틀려 잠겨 있으면 비밀번호가 맞아도 429
        member = await self.members.get_by_email(email)
        if not verify_password(password, member.password_hash if member else None):
            login_guard.failed(email)  # 없는 이메일도 똑같이 세요 (가입 여부를 알 수 없게)
            raise AuthenticationError(LOGIN_FAILED_MESSAGE)
        login_guard.succeeded(email)
        return create_access_token(member, self.settings)

    async def authenticate(self, token: str) -> CurrentUser:
        """토큰 → 로그인 사용자. 서명 · 만료 · 로그아웃 여부를 보고, 권한은 DB 의 현재 role 로 판단해요."""
        claims = decode_access_token(token, self.settings)
        if await self.blacklist.contains(claims.jti):
            raise AuthenticationError(LOGGED_OUT_MESSAGE)
        member = await self.members.get(claims.member_id)
        if member is None:  # 토큰 발급 뒤 탈퇴한 회원
            raise AuthenticationError("로그인 정보가 올바르지 않아요. 다시 로그인해 주세요.")
        return CurrentUser(member_id=member.id, email=member.email, role=member.role)

    async def get_member(self, member_id: int) -> Member:
        member = await self.members.get(member_id)
        if member is None:
            raise AuthenticationError("로그인 정보가 올바르지 않아요. 다시 로그인해 주세요.")
        return member

    async def logout(self, token: str) -> None:
        """토큰의 jti 를 만료 시각까지 블랙리스트에 넣어요. 그 뒤 같은 토큰은 401 이에요."""
        claims = decode_access_token(token, self.settings)
        await self.blacklist.purge_expired(datetime.now(UTC))
        await self.blacklist.add(claims.jti, claims.expires_at)
        await self.session.commit()
