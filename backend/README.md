# 구르망 백엔드 (FastAPI)

## 실행

```bash
cd backend
uv sync                       # Python 3.13 가상환경 + 의존성 설치
copy .env.example .env        # (macOS/Linux: cp) 후 값 수정
uv run alembic upgrade head   # DB 스키마 생성/갱신
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

## 인수 당시 코드

`legacy/` 폴더 참고 (기준 커밋 `9d162f6`).

## DB 마이그레이션 (Alembic)

```bash
uv run alembic revision --autogenerate -m "설명"   # 모델 변경 후 리비전 생성 → 파일 검토 필수
uv run alembic upgrade head                         # 적용
uv run alembic downgrade -1                         # 한 단계 되돌리기
```

- 새 `models.py` 는 `src/infrastructure/models.py` 에 import 한 줄을 추가해야 autogenerate 가 인식합니다.
- `alembic.ini` 에는 한글을 넣지 마세요 (Windows 에서 cp949 로 읽어 실패).
- 예전에 lifespan `create_all` 로 테이블을 만든 DB는 스키마가 같으면 `uv run alembic stamp head` 한 번이면 됩니다.
