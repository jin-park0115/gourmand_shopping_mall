# 통합 시나리오 점검 (SCRUM-46)

확인일: 2026-10-26 · `develop` (`dc0e754`) 기준
흐름: **회원가입 → 담기 → 주문 → 관리자 배송 → 고객 취소 시도 차단**, 그리고 관련 기존 기능(검색 · 필터 · 404) 회귀 확인

| 방법 | 내용 | 결과 |
|---|---|---|
| 자동 테스트 | [`backend/tests/test_integration_scenario.py`](../../backend/tests/test_integration_scenario.py) 3개 (테스트 DB, 실제 회원가입 · 로그인 토큰 사용) | ✅ 3 passed |
| 전체 백엔드 테스트 | `uv run pytest` | ✅ 396 passed |
| 실제 서버 | 임시 DB(마이그레이션 + 시드)로 띄운 백엔드에 HTTP 요청, 단계마다 DB 재조회 | ✅ 아래 기록 |
| 프론트 정적 검사 | `npx tsc --noEmit` · `npm run lint` | ✅ 오류 0 (lint 경고 17개는 기존 `<img>` 권고) |

## 시나리오 (실제 서버 · 임시 DB)

UC A(상품) · B(회원 · 장바구니 · 주문) · C(관리자 주문)가 한 주문으로 이어져요. 토큰 값은 기록에서 뺐어요.

| # | 단계 | 요청 | 응답 | DB 재조회 |
|---|---|---|---|---|
| 1 | 회원가입 · 로그인 | `POST /auth/signup` → `POST /auth/login` | 201 `role: customer` → 200 | |
| 2 | 상품 검색 (A) | `GET /products?q=곤약 젤리` | 200, 2개 (띄어쓰기 무시) | 3번 상품 재고 **60** |
| 3 | 장바구니 담기 (B) | `POST /cart/items` 2개 | 200 `totalCount 2 · totalPrice 7800` | |
| 4 | 주문하기 (B) | `POST /orders` | 201 `접수`, 결제 `결제완료` 7800 | 재고 **60 → 58**, 장바구니 **0줄** |
| 5 | 고객이 관리자 API 호출 | `PATCH /admin/orders/1/status` (고객 토큰) | **403** `FORBIDDEN` 관리자만 사용할 수 있어요. | |
| 6 | 관리자 주문 찾기 (C) | `GET /admin/orders?q=김구르` | 200, 1건 | |
| 7 | 관리자 상품준비중 (C) | `PATCH …/status {"status":"상품준비중"}` | 200, `nextStatuses: [배송중, 주문취소]` | |
| 8 | 관리자 배송중 (C) | `PATCH …/status {"status":"배송중","courier":"CJ대한통운","trackingNo":"1234-5678-9012"}` | 200, `nextStatuses: [배송완료, 배송지연]` | |
| 9 | 고객 주문 조회 (B) | `GET /orders/1` | 200 `배송중` | |
| 10 | **고객 취소 시도** | `POST /orders/1/cancel` | **409** `BUSINESS_RULE_VIOLATION` '배송중' 상태의 주문은 취소할 수 없어요. 고객센터에 문의해 주세요. | 주문 `배송중` · 결제 `결제완료` · 재고 **58 그대로** (복구 없음) |
| 11 | 관리자 배송완료 → 고객 취소 시도 | `PATCH …/status {"status":"배송완료"}` → `POST /orders/1/cancel` | 200 `nextStatuses: []` → **409** '배송완료' 상태의 주문은 취소할 수 없어요. … | |

10단계 직후 상태 이력 (`order_status_history`):

```
 from_status | to_status  | changed_by
 null        | 접수        | null        ← 주문 생성 (B)
 접수         | 상품준비중   | 6 (관리자)
 상품준비중    | 배송중      | 6 (관리자)
                                         ← 막힌 고객 취소는 이력을 남기지 않아요
```

자동 테스트는 같은 흐름에 더해 다음도 확인해요.

- 같은 상품을 두 번 담으면 수량이 합쳐지고, 주문 직후 `GET /cart` 가 비어 있어요.
- 배송완료 뒤에는 관리자도 `주문취소`로 바꿀 수 없어요 (409).
- 비교용 `test_customer_cancel_is_allowed_before_shipping`: **출고 전(`접수`)이면 같은 고객 취소가 200**이고, 재고 10 → 7 → 10, 결제 `결제취소`, 이력 `접수 → 주문취소` (`changed_by` null = 고객).

## 회귀: 검색 · 필터 · 404 (실제 서버)

| # | 기능 | 요청 | 결과 |
|---|---|---|---|
| R1 | 띄어쓰기 무시 검색 | `GET /products?q=도쿄바나나` | 200, 1개 ("도쿄 바나나 4개입") |
| R2 | 나라 필터 | `GET /products?country=japan` | 200, 10개 |
| R3 | 카테고리 필터 | `GET /products?category=candy` | 200, 12개 |
| R4 | 정렬 | `GET /products?sort=low` | 200, 60개 |
| R5 | 없는 나라 | `GET /products?country=korea` | 422 `VALIDATION_ERROR` country: 'japan', 'taiwan', 'china', 'vietnam', 'other' 중 하나로 보내 주세요. |
| R6 | 없는 상품 | `GET /products/999999` | 404 `NOT_FOUND` 상품을 찾을 수 없어요. |
| R7 | 없는 경로 | `GET /no-such-path` | 404 `NOT_FOUND` 요청한 주소를 찾을 수 없어요. |

자동 테스트 `test_existing_search_filter_and_404_still_work` 도 검색 · 결과 없음 · 가격 정렬 · 카테고리 필터 · 422 · 404 를 확인해요.

## 점검 중 발견한 것

| 내용 | 판단 | 처리 |
|---|---|---|
| 비회원이 장바구니 담기 · 장바구니 아이콘을 누르면 안내 없이 로그인 화면으로 이동 | 사실 | 확인 창 "장바구니는 로그인한 회원만 쓸 수 있어요. 로그인 화면으로 이동할까요?" (담기 버튼 · 헤더 · 모바일 탭, `lib/api.ts` `askLogin`) |
| 구매하지 않은 회원도 리뷰 작성 가능 | 사실 | **배송완료된 주문으로 받은 상품만** 작성 (403 `FORBIDDEN`), 작성 폼 표시용 `GET /products/{id}/reviews/writable` 추가. 테스트 `test_review_api.py` |
| 마이페이지 주문 내역 405 | 코드 문제 아님 | `GET /orders` 는 SCRUM-31(10-26 11:45 머지)에서 생겼어요. 그 전 백엔드에는 같은 주소에 `POST` 만 있어 405 → **develop pull 후 백엔드 재시작**. 최신 서버에서는 관리자 상태 변경이 마이페이지에 바로 보여요 |
| UTF-8 이 아닌 요청 본문은 422 가 아니라 영어 400 `BAD_REQUEST` | 사실 (화면에서는 생기지 않음) | 기록만 |

## 화면

(화면 캡처는 아래 순서로 추가 예정. 이 PC 에서는 브라우저 자동화 도구가 조직 보안 정책으로 막혀 있어 직접 찍어요)

1. `/signup` 가입 → `/products` 검색 · 나라 필터 → 상세에서 담기
2. `/cart` → `/checkout` 주문 → `/order/complete`
3. `/admin` 로그인 → 상품준비중 → 배송중(택배사 · 운송장)
4. `/mypage` 에서 배송중 주문 취소 시도 → 409 안내 문구
5. 회귀: `/search?q=도쿄바나나`, `/country/japan`, `/category/candy`, `/products/999999` 404 화면

캡처에 쓴 계정 · 주문은 임시 DB 와 함께 지워요.
