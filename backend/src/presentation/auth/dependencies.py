"""로그인 · 권한 확인 의존성 (SCRUM-19). 다른 기능의 라우터에서 Depends 로 써요.

    @router.get("/cart")
    async def my_cart(user: CurrentUser = Depends(get_current_user)): ...   # 회원 (없으면 401)

    @router.patch("/admin/orders/{order_id}/status")
    async def change(admin: CurrentUser = Depends(require_admin)): ...      # 관리자 (고객이면 403)

    @router.get("/products/{product_id}/reviews")
    async def reviews(user: CurrentUser | None = Depends(get_optional_user)): ...  # 공개 (isMine 계산용)
"""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from application.auth.service import AuthService
from core.config import get_settings
from database import get_session
from domain.auth.member import CurrentUser
from domain.exceptions import AppError, AuthenticationError, PermissionDeniedError


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session, get_settings())


# auto_error=False: 토큰이 없을 때도 FastAPI 기본 영어 오류 대신 우리 형식({code, message})으로 401 을 내요
# tokenUrl 은 Swagger Authorize 버튼이 로그인할 주소예요
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme), service: AuthService = Depends(get_auth_service)
) -> CurrentUser:
    """로그인한 회원 (고객 · 관리자). 토큰이 없거나 · 만료 · 위조 · 로그아웃된 토큰이면 401."""
    if not token:
        raise AuthenticationError("로그인이 필요해요.")
    return await service.authenticate(token)


async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """관리자만. 로그인 문제는 401, 고객 계정이면 403. 돌려주는 user.member_id 를 이력의 changed_by 로 쓰면 돼요."""
    if not user.is_admin:
        raise PermissionDeniedError("관리자만 사용할 수 있어요.")
    return user


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme), service: AuthService = Depends(get_auth_service)
) -> CurrentUser | None:
    """공개 API 용: 올바른 토큰이면 회원, 없거나 만료 · 로그아웃된 토큰이면 None (오류를 내지 않아요)."""
    if not token:
        return None
    try:
        return await service.authenticate(token)
    except AppError:
        return None
