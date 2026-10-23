"""회원·인증 API 라우터 (표현 계층): 요청 검증 → 응용 서비스 호출 → 응답 변환."""
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
