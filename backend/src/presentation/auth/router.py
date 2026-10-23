"""회원·인증 API 라우터 (표현 계층): 요청 검증 → 응용 서비스 호출 → 응답 변환."""
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from application.auth.service import AuthService
from domain.auth.member import CurrentUser
from domain.exceptions import AuthenticationError
from presentation.auth.dependencies import get_auth_service, get_current_user, oauth2_scheme
from presentation.auth.schemas import MemberOut, SignupIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: str | None = Depends(oauth2_scheme),
    _: CurrentUser = Depends(get_current_user),  # 이미 로그아웃 · 만료된 토큰이면 여기서 401
    service: AuthService = Depends(get_auth_service),
) -> Response:
    if not token:  # get_current_user 가 먼저 막지만, 타입상 확인
        raise AuthenticationError("로그인이 필요해요.")
    await service.logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MemberOut)
async def me(
    user: CurrentUser = Depends(get_current_user), service: AuthService = Depends(get_auth_service)
) -> MemberOut:
    """내 정보. 프론트가 저장해 둔 토큰이 아직 유효한지 확인할 때도 써요."""
    return MemberOut.of(await service.get_member(user.member_id))
