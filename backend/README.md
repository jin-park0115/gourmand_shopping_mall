# 구르망 백엔드 (FastAPI)

## 실행

```bash
cd backend
uv sync                       # Python 3.13 가상환경 + 의존성 설치
copy .env.example .env        # (macOS/Linux: cp) 후 값 수정
uv run uvicorn main:app --app-dir src --reload
```

- Swagger UI: http://localhost:8000/docs
- 헬스 체크: http://localhost:8000/health
- 아키텍처 의존성 검사: `uv run pytest`

## 폴더 구조 (도메인 중심 4계층)

```
src/
├── main.py              # 앱·라우터·미들웨어·lifespan 조립
├── database.py          # 비동기 엔진·세션·Base
├── core/config.py       # 환경변수 설정
├── presentation/<기능>/  # router.py, schemas.py  → 요청·응답 검증, 서비스 호출
├── application/<기능>/   # service.py            → 업무 흐름·트랜잭션 조율
├── domain/<기능>/        # 순수 파이썬 클래스     → 업무 규칙·상태 변경 (FastAPI·SQLAlchemy 금지)
└── infrastructure/<기능>/ # models.py, repositories.py → ORM 모델·조회/저장·도메인 변환
```

기능: `auth`(회원·인증), `product`(상품), `review`(리뷰), `cart`(장바구니), `order`(주문), `admin`(관리자 주문 운영)

## 의존성 규칙

| 계층 | 참조 가능 | 참조 금지 |
| --- | --- | --- |
| presentation | application, domain | infrastructure 직접 접근 |
| application | domain, infrastructure | presentation |
| domain | (없음) | 다른 모든 계층, fastapi, sqlalchemy, pydantic |
| infrastructure | domain | presentation, application |

`tests/test_architecture.py` 가 위 규칙을 자동으로 검사합니다.

## 오류 응답 형식

모든 오류는 `{"code": "...", "message": "..."}` 형식으로 응답합니다. 업무 규칙 위반은 `domain/exceptions.py`의 예외를 raise 하면 `presentation/exception_handlers.py`가 상태 코드로 바꿔 줍니다.

| 예외 | 상태 | code |
| --- | --- | --- |
| `InvalidValueError` | 422 | `INVALID_VALUE` |
| `BusinessRuleError` | 409 | `BUSINESS_RULE_VIOLATION` |
| `ConflictError` | 409 | `CONFLICT` |
| `NotFoundError` | 404 | `NOT_FOUND` |
| `AuthenticationError` | 401 | `UNAUTHORIZED` (`WWW-Authenticate: Bearer` 헤더 포함) |
| `PermissionDeniedError` | 403 | `FORBIDDEN` |
| 요청 검증 실패 (Pydantic) | 422 | `VALIDATION_ERROR` (+ `errors`) |
| 예상하지 못한 오류 | 500 | `INTERNAL_SERVER_ERROR` (내부 정보는 로그에만) |

```python
from domain.exceptions import BusinessRuleError

raise BusinessRuleError("배송완료된 주문은 취소할 수 없어요.")
```

## CORS · 요청 로그

- 허용 출처는 `.env`의 `CORS_ORIGINS`(쉼표 구분, 기본 `http://localhost:3000`)로 정합니다.
- 모든 요청은 `METHOD 경로 → 상태 처리시간ms id=요청ID` 한 줄로 기록됩니다 (4xx는 WARNING, 5xx는 ERROR).
- 쿼리스트링(검색어에 이름 · 연락처가 들어갈 수 있음) · 헤더(토큰) · 본문(비밀번호)은 기록하지 않습니다. 같은 이유로 uvicorn 기본 접근 로그는 꺼 두었습니다.
- 응답 헤더 `X-Request-ID`, `X-Process-Time-Ms`로 요청 ID와 처리 시간을 확인할 수 있습니다. 500 오류 응답에도 `X-Request-ID`가 담겨서 이 ID로 서버 로그를 찾을 수 있습니다.

## 인수 당시 코드

`legacy/` 폴더 참고 (기준 커밋 `9d162f6`).
