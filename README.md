# 🍪 구르망 GOURMAND

> 세계의 과자를 한 곳에서, **세계 과자 할인점 온라인 쇼핑몰**

화면만 있던 쇼핑몰(크런치클럽 팀)을 **인수해서**, FastAPI + PostgreSQL 백엔드와 회원 · 리뷰 · 장바구니 · 주문 · 관리자 기능을 붙인 프로젝트입니다.

인수 팀: **안중섭**(팀장, 관리자 주문) · **박진**(상품 · 리뷰) · **윤강**(장바구니 · 주문)

| 배포 | 주소 |
|---|---|
| 쇼핑몰 | https://gourmand-shopping-mall.vercel.app |
| API (Swagger) | https://gourmand-api.onrender.com/docs |

> 무료 서버라 한동안 요청이 없으면 잠들어요. 첫 화면이 오류로 보이면 30~50초 뒤 새로고침해 주세요.

<br>

## 목차

1. [프로젝트 소개](#1-프로젝트-소개)
2. [인수 정보](#2-인수-정보)
3. [실행 방법](#3-실행-방법)
4. [구조](#4-구조)
5. [UC별 기여](#5-uc별-기여)
6. [구현 상태 (API · Mock · 미완료)](#6-구현-상태-api--mock--미완료)
7. [검증](#7-검증)
8. [완성 화면](#8-완성-화면)

<br>

## 1. 프로젝트 소개

해외여행에서 사 오던 그 나라 간식을 집에서 편하게 주문할 수 있는 **세계 과자 온라인 쇼핑몰**입니다.
일본 · 대만 · 중국 · 베트남 · 그 외 나라(미국 · 프랑스 · 뉴질랜드)의 과자 62종을 **나라별 · 카테고리별**로 둘러보고, 리뷰를 보고, 장바구니에 담아 주문할 수 있습니다.

```
메인 ─┬─ 나라별 (일본 · 대만 · 중국 · 베트남 · 그 외)
      ├─ 카테고리 (스낵·칩, 쿠키·비스킷, 케이크·베이커리, 초콜릿, 젤리·캔디, 육포·견과·별미)
      ├─ 검색
      └─ PICK (팀원 추천 큐레이션)
            ↓
      상품 목록 (나라 · 종류 필터, 정렬 5종)
            ↓
      상품 상세 (상품 정보, 수량 선택, 리뷰)
            ↓
      로그인 → 장바구니 → 주문하기 → 주문 완료 → 마이페이지(주문 내역)

관리자: /admin → 주문 목록 · 요약 · 상세 · 상태 변경(출고 · 배송 · 취소)
```

### 기술 스택

| 구분 | 사용 기술 |
|---|---|
| 프론트엔드 | Next.js 16 (App Router, `cacheComponents`), React 19, TypeScript, Tailwind CSS v4 |
| 백엔드 | FastAPI, SQLAlchemy 2 (async, asyncpg), Pydantic v2, Alembic, uv (Python 3.13) |
| 인증 | OAuth2 password + JWT, argon2 비밀번호 해시, 로그아웃 토큰 블랙리스트 |
| 데이터베이스 | PostgreSQL (로컬) |
| 협업 | GitHub (`feat/SCRUM-xx` 브랜치 → `develop` PR), Jira, Notion |

<br>

## 2. 인수 정보

| 항목 | 내용 |
|---|---|
| 원본 저장소 | `hiju200208-png/shopping_mall` |
| 인수 기준 커밋 | `9d162f6` (2026-10-13), 저장소 태그 `inherited-base` |
| 작업 저장소 | `jin-park0115/gourmand_shopping_mall` (Fork). 작업은 `develop`에 PR로 모으고, `main`은 보호 규칙(`protect_main`)으로 막아 둠 |

### 인수 당시 상태 → 지금

| 영역 | 인수 당시 | 지금 |
|---|---|---|
| 상품 데이터 | 프론트 `data/products.ts` 정적 Mock 60개 | PostgreSQL + `GET /products` (검색 · 필터 · 정렬 · 페이지) |
| 백엔드 | 동기 FastAPI, `/health` · `/health/db` 두 개뿐 (`backend/legacy/`에 보관) | 비동기 FastAPI 4계층, API 24개 |
| DB 스키마 | 상품 · 나라 · 카테고리 · 리뷰 테이블만 | 회원 · 장바구니 · 주문 · 주문 상태 이력 · 토큰 블랙리스트 추가, Alembic 마이그레이션 |
| 회원 | 없음 | 회원가입 · 로그인 · 로그아웃 (JWT) |
| 리뷰 | 상품의 평점 · 리뷰 수 숫자만 | 리뷰 목록 · 작성 · 수정 · 삭제 (1인 1리뷰) |
| 장바구니 | 브라우저 `sessionStorage` | 회원별 장바구니 API |
| 주문 | 브라우저 `localStorage` | 주문 API (재고 차감을 한 트랜잭션으로) |
| 관리자 | 예시 주문(`sampleOrders`)으로 그린 화면 | 관리자 로그인 + 주문 목록 · 요약 · 상세 · 상태 변경 API |
| 저장소 관리 | 루트 `.gitignore` 없음, `__pycache__` 추적 | `.gitignore` 정리, `main` 보호 규칙, `develop` PR 흐름 |

<br>

## 3. 실행 방법

> 필요한 것: **PostgreSQL** (18에서 확인), **Python 3.13 + [uv](https://docs.astral.sh/uv/)**, **Node.js 20.9+**
> 명령은 모두 저장소 루트(`gourmand_shopping_mall/`) 기준입니다. Windows는 `cp` 대신 `copy`를 쓰세요.

### ① DB 준비 (한 번만)

```bash
psql -U postgres -c "CREATE DATABASE gourmand;"
psql -U postgres -c "CREATE DATABASE gourmand_test;"   # pytest 용 (DATABASE_URL 의 DB 이름 + _test)
```

### ② 백엔드 (`backend/` 폴더, http://localhost:8000)

```bash
cd backend
uv sync                          # 가상환경 + 의존성
cp .env.example .env             # 값 수정 (아래 환경변수 표)
uv run alembic upgrade head      # 테이블 만들기 · 갱신
uv run python scripts/seed.py    # 나라 7 · 카테고리 6 · 상품 62 · 관리자/고객 계정 · 리뷰 153
uv run uvicorn main:app --app-dir src --reload
```

- Swagger: http://localhost:8000/docs (오른쪽 위 `Authorize`에 이메일 · 비밀번호로 로그인)
- 시드는 여러 번 실행해도 중복이 생기지 않아요.

### ③ 프론트엔드 (`gourmand/` 폴더, http://localhost:3000)

```bash
cd gourmand
npm install
cp .env.example .env.local       # 백엔드 주소 (기본 http://localhost:8000)
npm run dev
```

> `npm` 명령은 꼭 `gourmand` 폴더에서 실행하세요. 루트에서 실행하면 `package.json`을 못 찾아요(ENOENT).
> 백엔드가 꺼져 있으면 상품 화면은 오류 화면을 보여 줘요.

### 환경변수

**`backend/.env`** (`backend/.env.example` 복사)

| 이름 | 예시 | 설명 |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:비밀번호@localhost:5432/gourmand` | 앱이 쓰는 DB. pytest는 같은 서버의 `<DB 이름>_test`를 써요 |
| `CORS_ORIGINS` | `http://localhost:3000` | 프론트 주소 (쉼표로 여러 개) |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` 결과 | 토큰 서명 키. **32바이트 이상**으로 (짧으면 경고가 나고 위조에 약해요) |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | 로그인 유지 시간(분) |
| `ADMIN_EMAIL` · `ADMIN_PASSWORD` | `admin@gourmand.com` · (직접 정함) | 시드가 만드는 관리자 계정. 비밀번호가 비면 만들지 않아요 |
| `CUSTOMER_EMAIL` · `CUSTOMER_PASSWORD` | `customer@gourmand.com` · (직접 정함) | 시드가 만드는 시연용 고객 계정 |

**`gourmand/.env.local`** (`gourmand/.env.example` 복사)

| 이름 | 예시 | 설명 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | 백엔드 주소 |

> `.env` · `.env.local`은 커밋하지 않아요 (`.gitignore`에 있음).

### 시연 계정

- 관리자: `.env`의 `ADMIN_EMAIL` / `ADMIN_PASSWORD` → http://localhost:3000/admin
- 고객: `.env`의 `CUSTOMER_EMAIL` / `CUSTOMER_PASSWORD`, 또는 `/signup`에서 새로 가입
- 시드 리뷰 작성자(`reviewer1~5@seed.test`)는 로그인할 수 없어요.

### 배포 (운영)

```mermaid
flowchart LR
    user["브라우저"] --> vercel["Vercel<br>Next.js (gourmand/)"]
    user -- "로그인 · 리뷰 · 장바구니 (CORS)" --> render
    vercel -- "상품 화면 (서버 렌더링)" --> render["Render<br>FastAPI (backend/)"]
    render --> neon[("Neon PostgreSQL<br>Singapore")]
    gha["GitHub Actions<br>10분마다 /health"] -.-> render
```

| 서비스 | 설정 | 배포되는 때 |
|---|---|---|
| **Vercel** (프론트) | Root Directory `gourmand`, Production Branch `main`, 환경변수 `NEXT_PUBLIC_API_URL` | `main`에 push |
| **Render** (백엔드) | 저장소의 `render.yaml`(Blueprint): `uv sync` → 시작할 때 `alembic upgrade head` → uvicorn, `/health` 체크, Singapore | `main`에 push |
| **Neon** (DB) | `production` 브랜치, `aws-ap-southeast-1` | — |

**배포 흐름:** 기능은 `develop`에 PR로 모으고, 배포할 때 `develop` → `main` 릴리스 PR을 머지해요. 그러면 Vercel과 Render가 함께 배포돼요. DB 마이그레이션은 Render가 시작할 때 자동으로 적용돼요.

**Render 환경변수**

| 이름 | 값 |
|---|---|
| `DATABASE_URL` | Neon 콘솔의 Connection string(Direct, `-pooler` 아닌 것)을 그대로. `postgresql://…?sslmode=require&channel_binding=require`도 asyncpg 형식으로 자동 변환돼요 |
| `CORS_ORIGINS` | `https://gourmand-shopping-mall.vercel.app,http://localhost:3000` (끝 `/`는 있어도 무시) |
| `JWT_SECRET_KEY` | Render가 자동 생성 (`render.yaml`의 `generateValue`) |

**운영 관리자 계정:** 운영 DB에 한 번 시드를 실행해서 만들어요. 가입 API로는 관리자가 될 수 없어요.
```bash
cd backend
DATABASE_URL="<Neon 주소>" ADMIN_EMAIL="admin@gourmand.com" ADMIN_PASSWORD="<새 비밀번호>" uv run python scripts/seed.py
```
같은 명령을 다시 실행하면 비밀번호를 바꿀 수 있어요. 시드는 시연용 리뷰 150개도 함께 넣어요.

**잠들기 대비:** Render 무료 서버는 15분 동안 요청이 없으면 잠들어서, 깨어날 때 30~50초가 걸려요. `.github/workflows/keep-warm.yml`이 10분마다 `/health`를 불러 깨워 둬요. GitHub 예약 실행은 몇 분씩 늦을 수 있어서, **시연 직전에는 API 주소를 한 번 직접 열어 두세요.**

<br>

## 4. 구조

### 백엔드: 도메인 중심 4계층

```mermaid
flowchart LR
    client["브라우저 · Swagger"] --> P

    subgraph P["presentation (router · schemas)"]
        direction TB
        p1["요청 검증 · 인증 의존성<br>응답 변환 · 오류 → {code, message}"]
    end
    subgraph A["application (service)"]
        a1["업무 흐름 · 트랜잭션 commit/rollback"]
    end
    subgraph D["domain (순수 파이썬)"]
        d1["업무 규칙 · 상태 변경 · 도메인 예외<br>FastAPI · SQLAlchemy 사용 금지"]
    end
    subgraph I["infrastructure (models · repositories)"]
        i1["ORM 모델 · 조회/저장<br>ORM ↔ 도메인 변환"]
    end

    P --> A
    P --> D
    A --> D
    A --> I
    I --> D
    I --> DB[(PostgreSQL)]
```

| 계층 | 참조 가능 | 참조 금지 |
|---|---|---|
| presentation | application, domain | infrastructure 직접 접근 |
| application | domain, infrastructure | presentation |
| domain | (없음) | 다른 모든 계층, fastapi, sqlalchemy, pydantic |
| infrastructure | domain | presentation, application |

이 규칙은 `backend/tests/test_architecture.py`가 자동으로 검사해요.

```
backend/src/
├── main.py                 # 앱 · 라우터 · 미들웨어 조립
├── database.py             # 비동기 엔진 · 세션
├── core/config.py          # 환경변수
├── presentation/<기능>/     # router.py, schemas.py
├── application/<기능>/      # service.py
├── domain/<기능>/           # 업무 규칙 클래스, exceptions.py
└── infrastructure/<기능>/   # models.py, repositories.py, seed.py
```

기능: `auth`(회원 · 인증) · `product`(상품) · `review`(리뷰) · `cart`(장바구니) · `order`(주문) · `admin`(관리자 주문)

- 오류 응답은 모두 `{"code", "message"}` 한 가지 모양이에요. 화면은 `message`를 그대로 보여 줘요.
- 자세한 내용: [backend/README.md](backend/README.md) · API 명세 [docs/API.md](docs/API.md) · ERD [docs/ERD.md](docs/ERD.md)

### 프론트엔드

```
RootLayout (app/layout.tsx)
└── AuthProvider                     # 로그인 상태 (useAuth)
    └── CartProvider                 # 장바구니 (장바구니 API)
        ├── Header                   # 로고, 나라 메뉴, 검색, 장바구니 · 마이페이지, 로그인/로그아웃
        ├── {page}
        ├── Footer
        └── MobileTabBar
```

```
app/
├── page.tsx                 /                    메인 (배너 · 나라 메뉴 · 신상품 · 할인)
├── products/page.tsx        /products            상품 목록 (ProductResults · ProductFilters · ProductCard)
├── products/[id]/page.tsx   /products/1          상품 상세 (ProductPurchase · ProductReviews · 같은 나라 추천)
├── search/                  /search              검색
├── country/[slug]/          /country/japan       나라별 상품
├── category/ · [slug]/      /category/snack      카테고리
├── pick/[slug]/             /pick/...            PICK 큐레이션
├── login/ · signup/         /login · /signup     로그인 · 회원가입 (AuthForms, ?next= 로 돌아가기)
├── cart/                    /cart                장바구니 (CartView)
├── checkout/                /checkout            주문하기 (CheckoutForm)
├── order/complete/          /order/complete      주문 완료 (OrderComplete)
├── mypage/                  /mypage              주문 내역 (MyOrders)
├── admin/                   /admin               관리자 (AdminDashboard, 관리자만)
├── not-found.tsx · error.tsx                     404 · 오류 화면
```

| 파일 | 역할 |
|---|---|
| `lib/api.ts` | 백엔드 호출, 토큰 자동 첨부, 오류 → `ApiError`, 만료 · 로그아웃 토큰이면 로그인 화면으로 |
| `lib/auth.ts` | 회원가입 · 로그인 · 로그아웃 · 내 정보 |
| `lib/products.ts` · `lib/reviews.ts` | 상품 · 리뷰 API |
| `lib/orders.ts` · `lib/adminOrders.ts` | 주문 · 관리자 주문 API |

자세한 내용: [gourmand/README.md](gourmand/README.md)

<br>

## 5. UC별 기여

| UC | 담당 | 백엔드 API | 화면 | Jira |
|---|---|---|---|---|
| **A. 상품 · 리뷰** | 박진 | `GET /products` (검색 · 나라/카테고리 필터 · 정렬 5종 · 페이지), `GET /products/{id}`, `GET /categories`, 리뷰 `GET · POST /products/{id}/reviews`, `PATCH · DELETE /reviews/{id}` | 상품 목록 · 상세 · 나라 · 카테고리 · 검색을 API로 전환, 상세 리뷰 (작성 · 수정 · 삭제 · 더보기), 로그인 · 회원가입 화면과 API 클라이언트 | SCRUM-20~26, 37, 38 |
| **B. 장바구니 · 주문** | 윤강 | 회원 `POST /auth/signup · login · logout`, `GET /auth/me`, 장바구니 `GET · DELETE /cart`, `POST /cart/items`, `PATCH · DELETE /cart/items/{id}`, 주문 `POST /orders`, `GET /orders` (내 주문 · 상태 · 기간 필터), `GET /orders/{id}`, `POST /orders/{id}/cancel` | 장바구니 · 주문하기 · 주문 완료 · 마이페이지를 API로 전환 | SCRUM-18, 19, 27~31, 40, 41 |
| **C. 관리자 주문** | 안중섭 | `GET /admin/orders` (상태 · 기간 · 주문자 검색), `GET /admin/orders/summary`, `GET /admin/orders/{id}`, `PATCH /admin/orders/{id}/status` (취소 시 재고 복구) | 관리자 대시보드를 API로 전환, 관리자 로그인 가드 | SCRUM-32~36, 43, 44 |

**공통 작업**

| 작업 | 담당 |
|---|---|
| Fork · 브랜치 보호 · `.gitignore` · uv 전환 · 4계층 뼈대 (SCRUM-5, 6, 12, 13) | 박진 |
| 로컬 PostgreSQL 결정 · 비동기 DB 세션 (SCRUM-8, 14) | 윤강 |
| ERD · 시드 · 공통 예외 처리 · CORS · 요청 로그 (SCRUM-9, 15~17) | 안중섭 |
| 인수 상태 분석 · API 명세 · UC 규칙 확정 · 통합 시나리오 점검 (SCRUM-7, 10, 11, 46) | 공통 |

Jira 키 전체 표: [docs/jira-keys.md](docs/jira-keys.md)

<br>

## 6. 구현 상태 (API · Mock · 미완료)

2026-10-26 `develop` 기준입니다.

| 기능 | 상태 | 비고 |
|---|---|---|
| 상품 목록 · 상세 · 나라 · 카테고리 · 검색 | ✅ API | 요청할 때마다 렌더링 (재고 · 평점이 바로 반영) |
| 리뷰 목록 · 작성 · 수정 · 삭제 | ✅ API | 배송완료된 주문으로 받은 상품만 작성, 상품당 1인 1리뷰, 본인 리뷰만 수정 · 삭제 |
| 회원가입 · 로그인 · 로그아웃 | ✅ API | 토큰은 브라우저 `localStorage` |
| 장바구니 | ✅ API | 로그인 필요 |
| 주문하기 · 주문 완료 | ✅ API | 재고 차감 · 주문 생성을 한 트랜잭션으로 |
| 관리자 주문 목록 · 요약 · 상세 · 상태 변경 | ✅ API | 관리자 계정만 |
| 마이페이지 주문 내역 · 고객 취소 | ✅ API | 상태 · 기간 필터, 배송 전 주문만 취소 (재고 복구) |
| 배송지 기억 | ✅ API | 주문할 때 고르면 내 계정에 저장 (`GET /orders/saved-address`), 다른 회원 · 다른 브라우저와 섞이지 않아요 |
| PICK 큐레이션 | 정적 데이터 (의도) | `data/picks.ts`, 팀원 추천 목록이라 DB에 두지 않았어요 |
| 결제 · 찜 · 리뷰 사진 | ❌ 하지 않음 | 범위 밖 |
| 배포 | ✅ Vercel · Render · Neon | [배포 (운영)](#배포-운영) 참고. 무료 플랜이라 잠들 수 있어요 |

<br>

## 7. 검증

```bash
cd backend
uv run pytest            # 계층 규칙 · 도메인 · API · 실패 케이스 (gourmand_test DB)
cd ../gourmand
npm test                 # Vitest: lib 함수 · 검색창 · 로그인/가입 폼 · 토스트 (서버 · 브라우저 없이)
npx tsc --noEmit && npm run lint && npm run build

# e2e (Playwright): 실제 브라우저로 처음부터 끝까지. 백엔드(127.0.0.1:8000)를 먼저 켜 두세요. 프론트는 없으면 자동으로 켜요
npx playwright install chromium webkit   # 처음 한 번 (브라우저 내려받기)
npm run e2e              # 크롬 · Safari 엔진(WebKit) · 모바일(iPhone 13)
npx playwright test --ui # 화면을 보면서 하나씩
```

- PR · develop/main push마다 GitHub Actions([`.github/workflows/test.yml`](.github/workflows/test.yml))가 위 세 가지를 모두 돌려요 (약 2분). 빨간 X가 뜨면 머지 전에 확인하세요.
- e2e는 **로컬 DB**에 테스트 회원(`e2e-…@test.com`) · 주문을 만들어요. 운영 사이트에는 돌리지 마세요.

| UC | 실패 케이스 · 로그아웃 후 401 검증 |
|---|---|
| A 상품 · 리뷰 | [docs/verification/A-review-failures.md](docs/verification/A-review-failures.md) (Swagger · 화면 캡처, DB 재조회), `tests/test_review_failures.py` |
| B 장바구니 · 주문 | [docs/verification/B-cart-order-failures.md](docs/verification/B-cart-order-failures.md), `tests/test_cart_order_failures.py` |
| C 관리자 주문 | `tests/test_admin_failures.py`, `tests/test_admin_logout.py` |
| 통합 시나리오 | [docs/verification/integration-scenario.md](docs/verification/integration-scenario.md) (회원가입 → 주문 → 관리자 배송 → 고객 취소 차단), `tests/test_integration_scenario.py` |
| 최종 QA | [docs/verification/final-qa.md](docs/verification/final-qa.md) (8개 영역 점검, 수정 전 · 후 같은 요청 비교) |

- 모든 실패는 `{code, message}` 모양이에요. 형식 오류는 400이 아니라 **422 `VALIDATION_ERROR`**로 통일했어요.
- 로그아웃한 토큰은 블랙리스트에 들어가서, 같은 토큰으로 다시 요청하면 401이에요.

<br>

## 8. 완성 화면

### 메인

| PC | 모바일 |
|:---:|:---:|
| <img src="docs/images/main-pc.png" width="560" alt="메인 페이지 PC"> | <img src="docs/images/main-mobile.png" width="260" alt="메인 페이지 모바일"> |

### 상품 목록

| PC | 모바일 |
|:---:|:---:|
| <img src="docs/images/products-pc.png" width="560" alt="상품 목록 페이지 PC"> | <img src="docs/images/products-mobile.png" width="260" alt="상품 목록 페이지 모바일"> |

**나라별 상품**: 나라 아이콘 하나로 그 나라 간식만 모아 볼 수 있어요.

| PC | 모바일 |
|:---:|:---:|
| <img src="docs/images/country-pc.png" width="560" alt="일본 상품 페이지 PC"> | <img src="docs/images/country-mobile.png" width="260" alt="일본 상품 페이지 모바일"> |

### 상품 상세 · 리뷰

| 상세 PC | 상세 모바일 |
|:---:|:---:|
| <img src="docs/images/detail-pc.png" width="560" alt="상품 상세 페이지 PC"> | <img src="docs/images/detail-mobile.png" width="260" alt="상품 상세 페이지 모바일"> |

| 리뷰 | 로그인 |
|:---:|:---:|
| <img src="docs/images/reviews-pc.png" width="420" alt="상품 상세 리뷰"> | <img src="docs/images/login-pc.png" width="420" alt="로그인 화면"> |

<br>

---

상품 이미지는 학습용으로 사용되었으며, 저작권은 각 제조사에 있습니다.
