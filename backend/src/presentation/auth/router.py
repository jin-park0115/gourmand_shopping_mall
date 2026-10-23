"""회원·인증 API 라우터 (표현 계층): 요청 검증 → 응용 서비스 호출 → 응답 변환."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from application.auth.service import AuthService
from core.config import get_settings
from database import get_session
from presentation.auth.schemas import MemberOut, SignupIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session, get_settings())


@router.post("/signup", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupIn, service: AuthService = Depends(get_auth_service)) -> MemberOut:
    member = await service.signup(email=body.email, password=body.password, name=body.name, phone=body.phone)
    return MemberOut.of(member)


@router.post("/login", response_model=TokenOut)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: AuthService = Depends(get_auth_service)
) -> TokenOut:
    """OAuth2 password 방식: form 의 username 칸에 이메일을 넣어요 (Swagger Authorize 버튼과 호환)."""
    token, expires_in = await service.login(email=form.username, password=form.password)
    return TokenOut(access_token=token, expires_in=expires_in)
