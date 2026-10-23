"""모든 기능이 함께 쓰는 업무 예외.

순수 파이썬이라 도메인에서 바로 raise 할 수 있어요.
HTTP 상태 코드로 바꾸는 일은 표현 계층(presentation/exception_handlers.py)이 맡아요.
"""


class AppError(Exception):
    """업무 예외의 공통 부모. code는 프론트가 분기할 때 쓰는 고정 문자열이에요."""

    code = "APP_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidValueError(AppError):
    """값이 규칙에 맞지 않음 (예: 별점 6점, 수량 0개) → 422"""

    code = "INVALID_VALUE"


class BusinessRuleError(AppError):
    """현재 상태에서 허용되지 않는 요청 (예: 배송완료 주문 취소) → 409"""

    code = "BUSINESS_RULE_VIOLATION"


class ConflictError(AppError):
    """이미 있는 데이터와 충돌 (예: 같은 이메일 가입, 중복 리뷰) → 409"""

    code = "CONFLICT"


class NotFoundError(AppError):
    """요청한 리소스가 없음 → 404"""

    code = "NOT_FOUND"


class AuthenticationError(AppError):
    """로그인 정보나 토큰이 올바르지 않음 (만료 · 로그아웃된 토큰 포함) → 401"""

    code = "UNAUTHORIZED"


class PermissionDeniedError(AppError):
    """로그인은 했지만 권한이 없음 (예: 고객이 관리자 API 호출, 남의 리뷰 수정) → 403"""

    code = "FORBIDDEN"
