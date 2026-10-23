# API 명세 초안 (SCRUM-10)

> 기준: `develop` 의 라우터 prefix(`presentation/*/router.py`)와 ORM 모델(SCRUM-8), 도메인 규칙(SCRUM-16 · 32)
> 각자 담당 엔드포인트를 자기 절에 채워요. 지금은 **공통 규칙**과 **C 관리자 주문**만 작성돼 있어요.
> 최종본은 팀 Notion 표(메서드 · 경로 · 요청/응답 · 에러 코드 · 권한)로 옮깁니다.

## 공통 규칙

| 항목 | 내용 |
| --- | --- |
| 주소 | 개발 서버 `http://localhost:8000`, 문서 `http://localhost:8000/docs` |
| 인증 | `Authorization: Bearer <access_token>` (발급 · 검증은 SCRUM-18 · 19) |
| 권한 표기 | 공개 = 로그인 없이, 회원 = 로그인한 고객 · 관리자, 관리자 = `member.role = admin` |
| 필드 이름 | 요청 · 응답 JSON은 camelCase (프론트 `lib/orderStorage.ts` 타입과 같게, Pydantic alias 사용) — **팀 합의 필요** |
| 날짜 · 시간 | 응답은 ISO 8601 KST (`2026-10-23T14:05:00+09:00`), 날짜 필터는 `YYYY-MM-DD` 이고 끝 날짜를 포함 |
| 페이지네이션 | 요청 `page`(1부터) · `size`(1~100, 기본 20), 응답 `{ items, total, page, size, pages }` — **팀 합의 필요** |
| 주문 상태 | 한글 문자열 6개: `접수` `상품준비중` `배송중` `배송완료` `배송지연` `주문취소` |
| 추적 헤더 | 모든 응답에 `X-Request-ID` · `X-Process-Time-Ms` (SCRUM-17). 500 오류 때 이 ID로 서버 로그를 찾아요 |

### 오류 응답 형식 (SCRUM-16, 머지됨)

모든 오류는 같은 모양이에요. 프론트는 `code`로 분기하고 `message`를 그대로 보여 주면 돼요.

```json
{ "code": "BUSINESS_RULE_VIOLATION", "message": "'배송완료' 상태에서 '주문취소'(으)로 바꿀 수 없어요." }
```

| HTTP | code | 언제 |
| --- | --- | --- |
| 400 | `BAD_REQUEST` | 잘못된 요청 (라우터에서 400을 직접 낼 때) |
| 401 | `UNAUTHORIZED` | 토큰 없음 · 만료 · 로그아웃된 토큰 (응답 헤더 `WWW-Authenticate: Bearer`) |
| 403 | `FORBIDDEN` | 로그인은 했지만 권한 없음 (고객이 관리자 API 호출 등) |
| 404 | `NOT_FOUND` | 없는 리소스 · 없는 경로 |
| 405 | `METHOD_NOT_ALLOWED` | 경로는 있지만 메서드가 다름 |
| 409 | `BUSINESS_RULE_VIOLATION` | 지금 상태에서 허용되지 않는 요청 (상태 전이 위반 등) |
| 409 | `CONFLICT` | 이미 있는 데이터와 충돌 (같은 이메일 가입, 중복 리뷰) |
| 422 | `VALIDATION_ERROR` | 형식 오류 (타입 · 길이 · 필수 값). 필드별 내용은 `errors` 배열에 |
| 422 | `INVALID_VALUE` | 형식은 맞지만 업무 규칙상 틀린 값 (지원하지 않는 택배사 등) |
| 500 | `INTERNAL_SERVER_ERROR` | 예상하지 못한 오류. 내부 정보는 응답에 싣지 않아요 |

## A 상품 · 리뷰 (박진)

> 담당자가 채워 주세요. 관련 티켓: SCRUM-22 상품 목록, SCRUM-23 상품 상세, SCRUM-25 리뷰

## B 인증 · 장바구니 · 주문 (윤강)

> 담당자가 채워 주세요. 관련 티켓: SCRUM-18 회원가입 · 로그인, SCRUM-19 로그아웃, SCRUM-27 장바구니, SCRUM-29 · 31 주문

## C 관리자 주문 (안중섭)

모든 엔드포인트는 **관리자만** 쓸 수 있어요 (`require_admin`, SCRUM-19). 토큰이 없거나 로그아웃된 토큰이면 401, 고객 계정이면 403이에요.

| 메서드 | 경로 | 설명 | 권한 | 성공 | 오류 | 티켓 |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/admin/orders` | 주문 목록 (상태 · 기간 · 검색 · 페이지) | 관리자 | 200 | 401 · 403 · 422 | SCRUM-34 |
| GET | `/admin/orders/summary` | 대시보드 요약 (상태별 개수 · 오늘 매출 · TOP 5) | 관리자 | 200 | 401 · 403 · 422 | SCRUM-34 · 36 |
| GET | `/admin/orders/{orderId}` | 주문 상세 + 상태 이력 | 관리자 | 200 | 401 · 403 · 404 · 422 | SCRUM-34 · 33 |
| PATCH | `/admin/orders/{orderId}/status` | 상태 변경 (출고 · 배송완료 · 지연 · 취소) | 관리자 | 200 | 401 · 403 · 404 · 409 · 422 | SCRUM-35 · 33 |

### 응답 공통: AdminOrder

목록 · 상세 · 상태 변경이 같은 모양을 돌려줘요. `history`는 상세와 상태 변경 응답에만 들어 있어요.

```json
{
  "orderId": 17,
  "status": "배송중",
  "orderedAt": "2026-10-23T14:05:00+09:00",
  "totalPrice": 27800,
  "buyer": {
    "buyerName": "김구르",
    "phone": "010-1234-5678",
    "zipcode": "06236",
    "address1": "서울 강남구 테헤란로 123",
    "address2": "4층"
  },
  "items": [
    { "id": 3, "name": "로투스 비스코프", "imageUrl": "https://…/lotus.jpg", "price": 4500, "quantity": 2 }
  ],
  "courier": "CJ대한통운",
  "trackingNo": "1234-5678-9012",
  "adminNote": null,
  "nextStatuses": ["배송완료", "배송지연"],
  "history": [
    { "status": "접수", "at": "2026-10-23T14:05:00+09:00", "note": null },
    { "status": "상품준비중", "at": "2026-10-23T15:10:00+09:00", "note": null },
    { "status": "배송중", "at": "2026-10-24T09:30:00+09:00", "note": null }
  ]
}
```

| 필드 | 출처 | 설명 |
| --- | --- | --- |
| `orderId` | `orders.order_id` | 주문 번호 (정수) |
| `buyer.*` | `orders.recipient · phone · zipcode · address1 · address2` | 받는 사람 정보. `buyerName` = `recipient` |
| `items[].price` | `order_item.unit_price` | 주문 당시 가격 (지금 상품 가격이 아님) |
| `items[].name · imageUrl` | `product.name · image_url` | |
| `courier · trackingNo · adminNote` | `orders` 추가 컬럼 (C 제안, ERD 참고) | 컬럼 추가 합의 전에는 `null` |
| `nextStatuses` | 도메인 `ADMIN_TRANSITIONS` | 관리자가 지금 바꿀 수 있는 상태. 화면 버튼을 이 값으로 보여 줘요 |
| `history` | `order_status_history` (SCRUM-33) | 오래된 순. 첫 줄은 주문 생성(`접수`) |

### GET /admin/orders

주문 목록이에요. 최신 주문부터 (`ordered_at` 내림차순, 같으면 `order_id` 내림차순).

| 쿼리 | 타입 | 필수 | 기본 | 설명 |
| --- | --- | --- | --- | --- |
| `status` | 주문 상태 | - | 전체 | 6개 상태 중 하나 |
| `q` | 문자열 (최대 50자) | - | - | 주문번호(정확히 일치) · 받는 사람 이름 · 연락처 · 상품명(부분 일치) |
| `from` | `YYYY-MM-DD` | - | - | 주문일 시작 (KST) |
| `to` | `YYYY-MM-DD` | - | - | 주문일 끝 (그날 포함) |
| `page` | 정수 ≥ 1 | - | 1 | |
| `size` | 정수 1~100 | - | 20 | |

```http
GET /admin/orders?status=배송지연&from=2026-10-20&to=2026-10-23&page=1&size=20
Authorization: Bearer eyJ…
```

```json
{ "items": [ { "orderId": 17, "status": "배송지연", "…": "AdminOrder (history 제외)" } ], "total": 1, "page": 1, "size": 20, "pages": 1 }
```

| 오류 | code | 예 |
| --- | --- | --- |
| 422 | `VALIDATION_ERROR` | `status=취소`(없는 상태), `size=500`, `from=2026-13-01` |
| 422 | `INVALID_VALUE` | `from`이 `to`보다 늦음 → "시작일이 종료일보다 늦어요." |

### GET /admin/orders/summary

관리자 화면 위쪽 카드와 TOP 5에 쓰는 요약이에요. 쿼리 `q` · `from` · `to`는 목록과 같아요 (`status` · `page` 없음).

```json
{
  "total": 42,
  "statusCounts": { "접수": 5, "상품준비중": 3, "배송중": 10, "배송완료": 20, "배송지연": 1, "주문취소": 3 },
  "todayOrders": 4,
  "todaySales": 98000,
  "todayUnits": 11,
  "waitingShipment": 8,
  "topProducts": [ { "id": 3, "name": "로투스 비스코프", "imageUrl": "https://…/lotus.jpg", "units": 14 } ]
}
```

| 필드 | 계산 |
| --- | --- |
| `statusCounts` | 상태별 주문 수. 0건인 상태도 0으로 |
| `todayOrders` | 오늘(KST) 들어온 주문 수 (취소 포함) |
| `todaySales` · `todayUnits` | 오늘 주문 중 **취소 제외** 금액 합계 · 상품 수량 합계 |
| `waitingShipment` | 출고 전 주문 수 (`접수` + `상품준비중`) |
| `topProducts` | 취소 제외 주문 수량 상위 5개 |

`statusCounts` · `total` · `topProducts`는 `q` · `from` · `to` 조건을 따르고, `today…` 세 값은 조건과 상관없이 오늘 기준이에요.

### GET /admin/orders/{orderId}

| 경로 값 | 타입 | 설명 |
| --- | --- | --- |
| `orderId` | 정수 ≥ 1 | 주문 번호 |

성공하면 `history`를 포함한 AdminOrder를 돌려줘요.

| 오류 | code | 예 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | "주문을 찾을 수 없어요." |
| 422 | `VALIDATION_ERROR` | `orderId`가 숫자가 아님 |

### PATCH /admin/orders/{orderId}/status

주문 상태를 바꿔요. 취소도 이 API로 해요 (`status: "주문취소"`).

| 본문 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `status` | 주문 상태 | O | 바꿀 상태 |
| `courier` | 문자열 | 상품준비중 → 배송중일 때 | `CJ대한통운` `우체국택배` `한진택배` `롯데택배` 중 하나 |
| `trackingNo` | 문자열 | 상품준비중 → 배송중일 때 | 숫자와 `-`로 8~20자 |
| `note` | 문자열 (최대 300자) | 배송지연 · 주문취소일 때 | 사유. 이력과 `adminNote`에 남아요 |

```http
PATCH /admin/orders/17/status
Authorization: Bearer eyJ…
Content-Type: application/json

{ "status": "배송중", "courier": "CJ대한통운", "trackingNo": "1234-5678-9012" }
```

허용되는 상태 변경 (도메인 `domain/order/status.py`, SCRUM-32):

| 지금 상태 | 바꿀 수 있는 상태 | 함께 보낼 값 |
| --- | --- | --- |
| 접수 | 상품준비중 · 주문취소 | 취소는 `note` |
| 상품준비중 | 배송중 · 주문취소 | 배송중은 `courier` · `trackingNo`, 취소는 `note` |
| 배송중 | 배송완료 · 배송지연 | 지연은 `note` |
| 배송지연 | 배송중 · 배송완료 | 없음 (등록된 운송장 그대로 사용) |
| 배송완료 · 주문취소 | 없음 (끝난 주문) | |

한 번의 요청은 한 트랜잭션으로 처리해요. 중간에 실패하면 전부 되돌려요.

1. 주문을 잠그고(`SELECT … FOR UPDATE`) 읽어요. 동시에 두 관리자가 바꿔도 두 번째 요청은 바뀐 상태 기준으로 검사돼요.
2. 도메인 규칙으로 검사해요 (`change_by_admin`).
3. `orders.status`를 바꾸고, 출고면 택배사 · 운송장을, 사유가 있으면 `adminNote`를 저장해요.
4. `order_status_history`에 한 줄 추가해요 (바꾼 관리자 id 포함, SCRUM-33).
5. `주문취소`면 주문 상품 수량만큼 `product.stock`을 되돌리고, 결제 상태를 바꿔요 (결제 상태 값은 B와 합의).

| 오류 | code | 예 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | 없는 주문 |
| 409 | `BUSINESS_RULE_VIOLATION` | "'배송완료' 상태에서 '주문취소'(으)로 바꿀 수 없어요.", "이미 '배송중' 상태예요." |
| 422 | `INVALID_VALUE` | "배송중으로 바꾸려면 택배사와 운송장 번호가 필요해요.", "운송장 번호는 숫자와 '-'로 8~20자여야 해요.", "'배송지연'(으)로 바꾸려면 사유를 입력해 주세요." |
| 422 | `VALIDATION_ERROR` | `status`가 6개 값이 아님, `note` 300자 초과 |

### C 구현 전에 합의할 것

| 항목 | 누구와 | 내용 |
| --- | --- | --- |
| `require_admin` | 윤강 (SCRUM-19) | 관리자 확인 의존성 이름 · 위치, 로그아웃 토큰 401 |
| `orders` 컬럼 추가 | 윤강 (SCRUM-29) | `courier` · `tracking_no` · `admin_note` · `updated_at` (ERD의 C 제안) |
| 주문 생성 때 이력 첫 줄 | 윤강 (SCRUM-29) | 주문을 만들 때 `order_status_history`에 `접수` 한 줄을 같이 넣을지 |
| 취소 때 결제 상태 | 윤강 | `payment.status`를 무엇으로 바꿀지 |
| 재고 복구 | 박진 (SCRUM-21) | `product.stock`을 늘리는 방법 (Repository 함수 공유) |
| camelCase · Page 형식 | 팀 전체 | 위 공통 규칙 두 줄 |
| 화면용 주문번호 | 윤강 · 박진 | 지금은 정수 `orderId`. 화면에 `G20261023-0001` 같은 번호가 필요하면 컬럼 추가 |
