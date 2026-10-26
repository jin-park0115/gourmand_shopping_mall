# legacy

인수 당시(기준 커밋 `9d162f6`) 백엔드 코드를 참고용으로 보관합니다.
동기 SQLAlchemy(psycopg) 기반이며, 현재 서버(`src/`)에서는 사용하지 않습니다.

- `main.py` : `/health`, `/health/db` 두 개만 있던 FastAPI 앱
- `database.py` : 동기 엔진·세션
- `models.py` : Country·Category·Product·Review ORM → `src/infrastructure/` 로 이전
- `check_db.py`, `compare_products.py` : DB 스키마·상품 데이터 점검 스크립트
