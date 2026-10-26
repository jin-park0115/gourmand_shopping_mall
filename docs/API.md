# API 명세 초안 (SCRUM-10)

> 기준: `develop` 의 라우터 prefix(`presentation/*/router.py`)와 ORM 모델(SCRUM-8), 도메인 규칙(SCRUM-16 · 32)
> 각자 담당 엔드포인트를 자기 절에 채워요. 작성됨: **공통 규칙** · **A 상품 · 리뷰** · **C 관리자 주문**.
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
| 422 | `VALIDATION_ERROR` | 형식 오류 (타입 · 길이 · 필수 값). `message`는 `필드: 우리말 문장` (예: `rating: 5 이하로 입력해 주세요.`), 필드별 원문은 `errors` 배열에 |
| 422 | `INVALID_VALUE` | 형식은 맞지만 업무 규칙상 틀린 값 (지원하지 않는 택배사 등) |
| 500 | `INTERNAL_SERVER_ERROR` | 예상하지 못한 오류. 내부 정보는 응답에 싣지 않아요 |

## A 상품 · 리뷰 (박진)

프론트 `lib/products.ts` 의 `findProducts()` · `getProduct()` 와 `data/products.ts` 정적 배열을 서버로 옮기는 API예요.
응답 필드는 프론트 `types/product.ts` 와 같게 맞춰서 화면 코드를 최소로 고치게 해요.

| 메서드 | 경로 | 설명 | 권한 | 성공 | 오류 | 티켓 |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/products` | 상품 목록 (검색 · 나라/카테고리 필터 · 정렬 · 페이지) | 공개 | 200 | 422 | SCRUM-22 |
| GET | `/products/{productId}` | 상품 상세 | 공개 | 200 | 404 · 422 | SCRUM-23 |
| GET | `/categories` | 카테고리 6개 + 상품 수 | 공개 | 200 | - | SCRUM-22 |
| GET | `/products/{productId}/reviews` | 리뷰 목록 (최신순 · 페이지) | 공개 | 200 | 404 · 422 | SCRUM-25 |
| GET | `/products/{productId}/reviews/writable` | 내가 이 상품 리뷰를 쓸 수 있는지 (작성 폼 표시용) | 회원 | 200 | 401 · 404 | SCRUM-46 |
| POST | `/products/{productId}/reviews` | 리뷰 작성 (배송완료된 주문으로 받은 상품만) | 회원 | 201 | 401 · 403 · 404 · 409 · 422 | SCRUM-25 · 46 |
| PATCH | `/reviews/{reviewId}` | 내 리뷰 수정 | 회원 (본인) | 200 | 401 · 403 · 404 · 422 | SCRUM-25 |
| DELETE | `/reviews/{reviewId}` | 내 리뷰 삭제 | 회원 (본인) | 204 | 401 · 403 · 404 | SCRUM-25 |

### 응답 공통: Product

목록 · 상세가 같은 모양이에요.

```json
{
  "id": 3,
  "name": "오리히로 곤약젤리 사과&포도 12개입",
  "price": 4500,
  "discountPrice": 3900,
  "country": "일본",
  "countrySlug": "japan",
  "category": "젤리·캔디",
  "categorySlug": "candy",
  "imageUrl": "/images/products/3.webp",
  "description": "사과와 포도 두 가지 맛의 쫀득한 곤약젤리. …",
  "isNew": false,
  "rating": 4.8,
  "reviewCount": 74,
  "stock": 120,
  "isSoldOut": false,
  "deliveryDays": 3,
  "volume": 25,
  "unit": "g",
  "itemCount": 12,
  "origin": "일본",
  "foodType": "젤리",
  "manufacturer": "오리히로",
  "storageMethod": "직사광선을 피해 서늘한 곳에 보관"
}
```

| 필드 | 출처 | 설명 |
| --- | --- | --- |
| `id` | `product.product_id` | |
| `discountPrice` | `product.discount_price` | 할인 없으면 `null` (프론트 타입은 `undefined` 기대 → `?? undefined` 처리) |
| `country` · `countrySlug` | `country.name` · `country.slug` | slug는 `japan` `taiwan` `china` `vietnam`, 그 외 나라는 `other` (합의 2) |
| `category` · `categorySlug` | `category.name` · `category.slug` | 6개 분류 (합의 1) |
| `rating` | `review.rating` 평균 | 소수 첫째 자리 반올림, 리뷰 없으면 `0` |
| `reviewCount` | `review` 개수 | |
| `isSoldOut` | 계산 | `stock = 0` (도메인 `Product.is_sold_out`, SCRUM-21) |
| 나머지 | `product.*` 같은 이름 | snake_case → camelCase |

### GET /products

기존 `findProducts()` 규칙을 그대로 옮겨요.

| 쿼리 | 타입 | 필수 | 기본 | 설명 |
| --- | --- | --- | --- | --- |
| `q` | 문자열 (최대 50자) | - | - | 검색어. 대소문자 · 띄어쓰기 무시 ("도쿄 바나나" = "도쿄바나나"). 상품명 · 나라 · 카테고리 · 제조사 · 식품유형 · 설명에서 찾아요 |
| `country` | `japan` `taiwan` `china` `vietnam` `other` | - | 전체 | `other` = 앞의 4개국이 아닌 나라 |
| `category` | 카테고리 slug | - | 전체 | `GET /categories` 의 `slug` |
| `ids` | 쉼표로 구분한 정수 (최대 100개) | - | - | 픽 페이지용 (`ids=1,5,9`). 없는 id는 빠져요 |
| `sort` | `recommend` `review` `low` `high` `new` | - | `recommend` | 아래 표 |
| `page` | 정수 ≥ 1 | - | 1 | |
| `size` | 정수 1~100 | - | 20 | 메인 화면처럼 전체가 필요하면 `size=100` |

| sort | 이름 | 순서 |
| --- | --- | --- |
| `recommend` | 추천순 | 검색어가 상품명에 있는 상품 먼저 → 평점 높은 순 |
| `review` | 리뷰 많은순 | `reviewCount` 내림차순 |
| `low` | 낮은 가격순 | 판매가(`discountPrice` 있으면 그 값, 없으면 `price`) 오름차순 |
| `high` | 높은 가격순 | 판매가 내림차순 |
| `new` | 신상품순 | `isNew` 먼저 → `id` 내림차순 |

모든 정렬에서 **품절 상품은 맨 뒤**, 같은 순위면 `id` 오름차순이에요 (페이지가 바뀌어도 순서가 흔들리지 않게).

```http
GET /products?q=도쿄바나나&country=japan&sort=low&page=1&size=20
```

```json
{ "items": [ { "id": 4, "name": "도쿄 바나나 8개입", "…": "Product" } ], "total": 1, "page": 1, "size": 20, "pages": 1 }
```

| 오류 | code | 예 |
| --- | --- | --- |
| 422 | `VALIDATION_ERROR` | `sort=cheap`, `country=korea`, `size=500`, `ids=a,b`, `q` 50자 초과 |

없는 `category` slug는 오류가 아니라 빈 목록(`total: 0`)이에요. 화면은 "결과 없음"을 보여 주면 돼요.

### GET /products/{productId}

| 경로 값 | 타입 | 설명 |
| --- | --- | --- |
| `productId` | 정수 ≥ 1 | 상품 번호 |

성공하면 Product 하나를 돌려줘요.

| 오류 | code | 예 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | "상품을 찾을 수 없어요." → 프론트 `notFound()` 로 `app/not-found.tsx` 화면 |
| 422 | `VALIDATION_ERROR` | `productId` 가 숫자가 아님 |

### GET /categories

카테고리 화면(`app/category/page.tsx`)의 "N개" 표시가 지금은 `lib/categories.ts` 의 손으로 적은 `productIds` 길이예요. 상품이 DB로 옮겨 가면 이 숫자가 실제와 어긋나서 서버에서 세어 줘요.
소개 문구(`desc`) · 대표 이미지(`imageId`)는 화면 꾸밈이라 프론트에 그대로 둬요.

```json
[
  { "slug": "snack", "name": "스낵·칩", "productCount": 16 },
  { "slug": "cookie", "name": "쿠키·비스킷", "productCount": 8 },
  { "slug": "candy", "name": "젤리·캔디", "productCount": 12 }
]
```

나라 목록 API는 만들지 않아요. 나라 메뉴 · 배너는 화면 고정값이고 상품 수를 보여 주지 않아요.

### 응답 공통: Review

```json
{
  "id": 12,
  "productId": 3,
  "authorName": "김구르",
  "rating": 5,
  "content": "식감이 쫀득해서 아이들이 좋아해요.",
  "createdAt": "2026-10-23T14:05:00+09:00",
  "updatedAt": null,
  "isMine": true
}
```

| 필드 | 출처 | 설명 |
| --- | --- | --- |
| `authorName` | `member.name` | 작성자 이름 (합의 4) |
| `updatedAt` | `review.updated_at` | 수정한 적 없으면 `null` |
| `isMine` | 계산 | 로그인한 요청이고 작성자가 본인이면 `true`. 토큰이 없으면 항상 `false` (합의 5) |

### GET /products/{productId}/reviews

최신순 (`created_at` 내림차순, 같으면 `review_id` 내림차순). 토큰은 **있어도 되고 없어도 돼요** (있으면 `isMine` 계산).

| 쿼리 | 타입 | 필수 | 기본 |
| --- | --- | --- | --- |
| `page` | 정수 ≥ 1 | - | 1 |
| `size` | 정수 1~50 | - | 10 |

```json
{ "items": [ { "id": 12, "…": "Review" } ], "total": 74, "page": 1, "size": 10, "pages": 8 }
```

| 오류 | code | 예 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | 없는 상품 |
| 422 | `VALIDATION_ERROR` | `size=100` |

### POST /products/{productId}/reviews

| 본문 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `rating` | 정수 1~5 | O | 별점 |
| `content` | 문자열 10~1000자 (앞뒤 공백 제거 후) | O | 내용 |

```http
POST /products/3/reviews
Authorization: Bearer eyJ…
Content-Type: application/json

{ "rating": 5, "content": "식감이 쫀득해서 아이들이 좋아해요." }
```

성공하면 `201` 과 만든 Review(`isMine: true`)를 돌려줘요.

| 오류 | code | 예 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 토큰 없음 · 만료 · 로그아웃된 토큰 |
| 403 | `FORBIDDEN` | "배송완료된 주문의 상품만 리뷰를 쓸 수 있어요." (내 주문 중 이 상품이 든 `배송완료` 주문이 없음. 접수 ~ 배송지연 · 주문취소는 안 돼요) |
| 404 | `NOT_FOUND` | 없는 상품 |
| 409 | `CONFLICT` | "이미 이 상품에 리뷰를 작성했어요." (상품당 1인 1리뷰, DB UNIQUE로도 막아요) |
| 422 | `VALIDATION_ERROR` | `rating=6`, `content` 10자 미만 · 1000자 초과 |

### GET /products/{productId}/reviews/writable

상품 상세에서 작성 폼을 보여 줄지 정할 때 써요. 등록할 때도 서버가 같은 규칙으로 다시 검사해요.

```json
{ "canWrite": false, "message": "배송완료된 주문의 상품만 리뷰를 쓸 수 있어요." }
```

쓸 수 있으면 `{ "canWrite": true, "message": null }` 이에요. 이미 쓴 리뷰가 있는지는 목록의 `isMine` 으로 봐요.

### PATCH /reviews/{reviewId}

보낸 필드만 바꿔요. 둘 다 생략하면 422.

| 본문 | 타입 | 필수 |
| --- | --- | --- |
| `rating` | 정수 1~5 | - |
| `content` | 문자열 10~1000자 | - |

성공하면 바뀐 Review(`updatedAt` 채워짐)를 돌려줘요.

| 오류 | code | 예 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | |
| 403 | `FORBIDDEN` | "본인이 작성한 리뷰만 수정할 수 있어요." (관리자도 남의 리뷰는 수정 불가) |
| 404 | `NOT_FOUND` | 없는 리뷰 |
| 422 | `VALIDATION_ERROR` | 바꿀 값 없음, 범위 밖 |

### DELETE /reviews/{reviewId}

성공하면 `204` (본문 없음). 오류는 PATCH와 같아요 (403 메시지 "본인이 작성한 리뷰만 삭제할 수 있어요.").

### A 구현 전에 합의할 것 (모두 반영됨)

| # | 항목 | 누구와 | 내용 | 결과 |
| --- | --- | --- | --- | --- |
| 1 | 카테고리 기준 통일 | 안중섭 (SCRUM-15) | DB `category`(과자 · 젤리·캔디 …)와 프론트 `lib/categories.ts`(6개 분류, 상품 번호로 묶음)가 달라요. `category.slug` 컬럼을 추가하고 시드를 프론트 6개 분류로 맞추자는 제안 | ✅ SCRUM-15 · 21 |
| 2 | 나라 slug | 안중섭 (SCRUM-15) | `country.slug` 컬럼 추가 (`japan` `taiwan` `china` `vietnam`, 나머지는 slug 없이 `other` 로 응답) | ✅ SCRUM-21 |
| 3 | 평점 · 리뷰 수 | 안중섭 (SCRUM-15) | DB에 컬럼이 없어서 `review` 에서 집계해요. 시드에 리뷰가 없으면 처음엔 모두 0 → 시드 리뷰를 넣을지 | ✅ SCRUM-25: 리뷰 작성용 회원 5명 · 리뷰 150개 시드 |
| 4 | `review.member_id` | 윤강 (SCRUM-18) | 지금 `review` 에는 `author_name` 만 있어 1인 1리뷰 · 본인 확인을 못 해요. `member_id` FK + `(product_id, member_id)` UNIQUE + `updated_at` 추가, `author_name` 제거 | ✅ SCRUM-25 마이그레이션 `a4f3fa9ce8d9` |
| 5 | 선택 로그인 의존성 | 윤강 (SCRUM-19) | 리뷰 목록의 `isMine` 용으로 "토큰 있으면 회원, 없으면 None" 을 돌려주는 `get_optional_user` | ✅ SCRUM-19 |
| 6 | 재고 변경 함수 | 안중섭 (SCRUM-35) · 윤강 (SCRUM-29) | ProductRepository 에 `decrease_stock` · `increase_stock` 를 두고 주문 · 취소에서 같이 써요 (SCRUM-21) | ✅ `get_for_update` + `decrease_stock` · `increase_stock` + `save_stock` |

컬럼 변경(1 · 2 · 4)은 합의되면 SCRUM-21 에서 Alembic 리비전으로 넣어요.

## B 인증 · 장바구니 · 주문 (윤강)

> 관련 티켓: SCRUM-18 회원가입 · 로그인, SCRUM-19 로그아웃, SCRUM-27 장바구니, SCRUM-29 · 31 주문 (장바구니 · 주문은 추가 예정)

| 메서드 | 경로 | 설명 | 권한 | 성공 | 오류 | 티켓 |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/auth/signup` | 회원가입 | 공개 | 201 | 409 · 422 | SCRUM-18 |
| POST | `/auth/login` | 로그인 (access token 발급) | 공개 | 200 | 401 · 422 | SCRUM-18 |
| POST | `/auth/logout` | 로그아웃 (지금 토큰을 블랙리스트에) | 회원 | 204 | 401 | SCRUM-19 |
| GET | `/auth/me` | 내 정보 (토큰이 아직 유효한지 확인용) | 회원 | 200 | 401 | SCRUM-19 |
| GET | `/cart` | 내 장바구니 | 회원 | 200 | 401 | SCRUM-27 |
| POST | `/cart/items` | 담기 (같은 상품이면 수량 합산) | 회원 | 200 | 401 · 404 · 409 · 422 | SCRUM-27 |
| PATCH | `/cart/items/{productId}` | 수량 변경 | 회원 | 200 | 401 · 404 · 409 · 422 | SCRUM-27 |
| DELETE | `/cart/items/{productId}` | 상품 빼기 | 회원 | 200 | 401 · 404 | SCRUM-27 |
| DELETE | `/cart` | 전체 비우기 | 회원 | 200 | 401 | SCRUM-27 |
| POST | `/orders` | 주문하기 (내 장바구니 전체) | 회원 | 201 | 401 · 404 · 409 · 422 | SCRUM-29 |
| GET | `/orders` | 내 주문 목록 (상태 · 기간 · 페이지) | 회원 | 200 | 401 · 422 | SCRUM-31 |
| GET | `/orders/{orderId}` | 내 주문 하나 (주문 완료 화면) | 회원 (본인) | 200 | 401 · 403 · 404 | SCRUM-29 · 31 |
| POST | `/orders/{orderId}/cancel` | 고객 취소 (접수 · 상품준비중만) | 회원 (본인) | 200 | 401 · 403 · 404 · 409 | SCRUM-31 |

### POST /auth/signup

```json
{ "email": "kim@gourmand.com", "password": "secret-123", "name": "김구르", "phone": "010-1234-5678" }
```

| 필드 | 규칙 |
| --- | --- |
| `email` | 이메일 형식. 소문자로 저장해요 (`Kim@A.com` 과 `kim@a.com` 은 같은 계정) |
| `password` | 8~64자. argon2 로 해싱해서 저장해요 |
| `name` | 1~50자 |
| `phone` | 선택. 숫자와 `-` 9~20자 |

응답 (201): `{ "id", "email", "name", "phone", "role" }` — 가입하면 `role` 은 항상 `customer` 예요.

| 오류 | code | 예 |
| --- | --- | --- |
| 409 | `CONFLICT` | "이미 가입된 이메일이에요." |
| 422 | `VALIDATION_ERROR` | 이메일 형식 · 비밀번호 길이 · 이름 길이 |

### POST /auth/login

OAuth2 password 방식이라 **form** (`application/x-www-form-urlencoded`) 으로 보내요. `username` 칸에 이메일을 넣어요 (Swagger `Authorize` 버튼과 호환).

```
username=kim@gourmand.com&password=secret-123
```

응답 (200) — OAuth2 표준이라 이 응답만 snake_case 예요.

```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 3600 }
```

토큰(JWT HS256)에는 `sub`(member_id, 문자열) · `role` · `jti`(토큰 id, 로그아웃 블랙리스트용) · `exp` · `iat` 가 들어 있어요.
이메일이 없을 때와 비밀번호가 틀렸을 때 모두 같은 401 "이메일 또는 비밀번호가 올바르지 않아요." 예요 (가입 여부가 드러나지 않게).

### POST /auth/logout · GET /auth/me

`Authorization: Bearer <access_token>` 을 보내요. 로그아웃하면 그 토큰의 `jti` 를 만료 시각까지 `token_blacklist` 에 넣어서, 같은 토큰으로 다시 요청하면 401 "로그아웃된 토큰이에요. 다시 로그인해 주세요." 예요. 다른 기기에서 받은 토큰은 그대로 쓸 수 있어요.
`GET /auth/me` 응답은 회원가입 응답과 같은 `{ id, email, name, phone, role }` 이에요.

### 로그인 · 권한 의존성 (다른 기능에서 쓰는 법)

`presentation/auth/dependencies.py` 에서 import 해서 `Depends` 로 써요. 모두 `CurrentUser(member_id, email, role)` 를 돌려줘요. `role` 은 토큰이 아니라 **DB 의 현재 값**이라, 관리자 권한을 바꾸면 다시 로그인하지 않아도 바로 반영돼요.

| 의존성 | 쓰는 곳 | 토큰 없음 · 만료 · 위조 · 로그아웃 | 고객 계정 |
| --- | --- | --- | --- |
| `get_current_user` | 회원 API (장바구니 · 주문 · 리뷰 작성) | 401 | 통과 |
| `require_admin` | 관리자 API | 401 | 403 "관리자만 사용할 수 있어요." |
| `get_optional_user` | 공개 API 인데 로그인 여부로 값이 달라질 때 (리뷰 `isMine`) | `None` (오류 없음) | 통과 |

```python
from presentation.auth.dependencies import get_current_user, require_admin
from domain.auth.member import CurrentUser

@router.patch("/admin/orders/{order_id}/status")
async def change_status(order_id: int, admin: CurrentUser = Depends(require_admin), ...):
    ...  # admin.member_id 를 이력의 changed_by 로
```

Swagger(`/docs`) 오른쪽 위 `Authorize` 에 이메일 · 비밀번호를 넣으면 로그인된 상태로 시험할 수 있어요.

### 장바구니 (SCRUM-27)

모두 로그인한 **본인** 장바구니만 다뤄요 (경로에 회원 번호가 없어요). 조회뿐 아니라 담기 · 변경 · 삭제도 **바뀐 뒤 장바구니 전체**를 돌려줘서, 프론트는 응답으로 바로 화면을 갱신하면 돼요.

```json
{
  "items": [
    { "id": 6, "name": "로투스 비스코프", "imageUrl": "/images/6.png", "price": 3900,
      "quantity": 2, "stock": 5, "isSoldOut": false, "subtotal": 7800 }
  ],
  "totalCount": 2,
  "totalPrice": 7800
}
```

| 필드 | 설명 |
| --- | --- |
| `id` | 상품 번호 (프론트 `CartItem.id` 와 같아요) |
| `price` | **지금** 판매가 (할인가가 있으면 할인가). 담은 시점 가격을 따로 저장하지 않아요 |
| `isSoldOut` | 담아 둔 사이 품절되면 `true` → 주문 전에 빼도록 안내 |
| 순서 | 먼저 담은 상품이 위 |

요청 본문: `POST /cart/items` 는 `{ "productId": 6, "quantity": 2 }` (`quantity` 생략하면 1), `PATCH` 는 `{ "quantity": 3 }`.

| 오류 | code | 예 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | "상품을 찾을 수 없어요.", "장바구니에 없는 상품이에요." |
| 409 | `BUSINESS_RULE_VIOLATION` | "'로투스' 상품이 품절이에요.", "'로투스' 재고가 부족해요. (최대 5개까지 담을 수 있어요)" — 합친 수량이 재고를 넘어도 409, 장바구니는 그대로 |
| 422 | `VALIDATION_ERROR` | 수량 0 이하 · 999 초과 |

### 주문하기 (SCRUM-29)

`POST /orders` 는 **배송 정보만** 받아요. 주문 상품 · 수량 · 가격은 서버 장바구니에서 가져와서, 화면이 보낸 가격을 믿지 않아요.

```json
{ "recipient": "김구르", "phone": "010-1234-5678", "zipcode": "06236", "address1": "서울 강남구 테헤란로 123", "address2": "4층" }
```

| 필드 | 규칙 (프론트 CheckoutForm 과 같아요) |
| --- | --- |
| `recipient` | 받는 분, 비우면 안 돼요 (50자까지) |
| `phone` | 휴대폰 `01X-XXXX-XXXX` (`-` 생략 가능) |
| `zipcode` | 숫자 5자리 |
| `address1` · `address2` | 주소 (필수) · 상세 주소 (선택, 비우면 `null`) |

한 트랜잭션으로 처리해요: 장바구니 잠금 → 상품을 상품 번호 순으로 잠그고 재고 차감 → 주문 · 주문 상품(주문 당시 판매가) · 결제(`결제완료`, 결제 연동이 없어 바로 완료) 저장 → 상태 이력 첫 줄(`null → 접수`) → 장바구니 비우기.
**하나라도 실패하면 전부 되돌려요** (앞 상품 재고도 그대로, 장바구니도 그대로).

응답 (201) · `GET /orders/{orderId}`:

```json
{
  "orderId": 12, "status": "접수", "orderedAt": "2026-10-26T14:03:00", "totalPrice": 13800,
  "recipient": "김구르", "phone": "010-1234-5678", "zipcode": "06236", "address1": "서울 강남구 테헤란로 123", "address2": "4층",
  "items": [{ "productId": 6, "name": "로투스 비스코프", "imageUrl": "/images/6.png", "unitPrice": 3900, "quantity": 2, "subtotal": 7800 }],
  "payment": { "method": "카드", "amount": 13800, "status": "결제완료", "paidAt": "2026-10-26T14:03:00" }
}
```

`orderedAt` · `paidAt` 은 KST (시간대 표시 없음, 관리자 화면과 같은 기준). 없는 주문은 404, **남의 주문은 403** "본인 주문만 볼 수 있어요." (SCRUM-31 Jira 규칙)

| 오류 | code | 예 |
| --- | --- | --- |
| 403 | `FORBIDDEN` | "본인 주문만 볼 수 있어요." (`GET /orders/{orderId}`) |
| 404 | `NOT_FOUND` | "주문을 찾을 수 없어요." |
| 409 | `BUSINESS_RULE_VIOLATION` | "장바구니가 비어 있어요.", "'하리보' 재고가 부족해요. (남은 수량 4개)", "'로투스' 상품이 품절이에요." |
| 422 | `INVALID_VALUE` | "휴대폰 번호를 올바르게 입력해 주세요. (예: 010-1234-5678)", "우편번호 5자리를 입력해 주세요." |

### 내 주문 목록 · 고객 취소 (SCRUM-31)

`GET /orders` — 내 주문만, **최근 주문이 먼저**. 응답은 공통 `Page` 형식이고 `items` 는 위 주문 응답과 같아요.

| 쿼리 | 설명 |
| --- | --- |
| `status` | 6개 주문 상태 중 하나 (없으면 전체) |
| `from` · `to` | 주문일 `YYYY-MM-DD` (KST), `to` 는 그날 하루 전체 포함 — 관리자 목록과 같은 규칙 |
| `page` · `size` | 기본 1 · 10, `size` 최대 50 |

`POST /orders/{orderId}/cancel` — 본문 없음. 한 트랜잭션으로 주문 잠금 → 상태 `주문취소` → 이력 한 줄(`changed_by` 없음 = 고객 취소) → **재고 복구**(상품 번호 순서로 잠금) → 결제 `결제취소`. 바뀐 주문을 돌려줘요.

| 오류 | code | 예 |
| --- | --- | --- |
| 403 | `FORBIDDEN` | "본인 주문만 볼 수 있어요." (남의 주문) |
| 404 | `NOT_FOUND` | "주문을 찾을 수 없어요." |
| 409 | `BUSINESS_RULE_VIOLATION` | "'배송중' 상태의 주문은 취소할 수 없어요. 고객센터에 문의해 주세요." (접수 · 상품준비중이 아니면, 이미 취소한 주문도) |
| 422 | `VALIDATION_ERROR` · `INVALID_VALUE` | 없는 상태 값, `from` 이 `to` 보다 늦음, `size` 50 초과 |

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
| `courier · trackingNo · adminNote` | `orders.courier · tracking_no · admin_note` (SCRUM-35 리비전) | 출고 전에는 `courier · trackingNo`가 `null`, 사유를 남긴 적이 없으면 `adminNote`가 `null` |
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
5. `주문취소`면 주문 상품 수량만큼 `product.stock`을 되돌리고(상품을 `product_id` 순서로 잠근 뒤 `increase_stock`), 결제 상태를 `결제취소`로 바꿔요. 결제 행이 없는 주문은 결제 쪽을 건너뛰어요.

| 오류 | code | 예 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | 없는 주문 |
| 409 | `BUSINESS_RULE_VIOLATION` | "'배송완료' 상태에서 '주문취소'(으)로 바꿀 수 없어요.", "이미 '배송중' 상태예요." |
| 422 | `INVALID_VALUE` | "배송중으로 바꾸려면 택배사와 운송장 번호가 필요해요.", "운송장 번호는 숫자와 '-'로 8~20자여야 해요.", "'배송지연'(으)로 바꾸려면 사유를 입력해 주세요." |
| 422 | `VALIDATION_ERROR` | `status`가 6개 값이 아님, `note` 300자 초과 |

### C 구현 전에 합의할 것

| 항목 | 누구와 | 내용 | 상태 |
| --- | --- | --- | --- |
| `require_admin` | 윤강 (SCRUM-19) | 위치 `presentation/auth/dependencies.py`. 통과하면 `CurrentUser(member_id, email, role)`를 돌려줘요. 토큰 없음 · 만료 · 로그아웃된 토큰은 401, 로그인했지만 `role`이 `admin`이 아니면 403 | 구현됨 (SCRUM-19) |
| `orders` 컬럼 추가 | 윤강 (SCRUM-29) | `courier` · `tracking_no` · `admin_note` · `updated_at` + `(status, ordered_at)` 인덱스 | 합의됨 |
| 주문 생성 때 이력 첫 줄 | 윤강 (SCRUM-29) | 주문을 만들 때 `order_status_history`에 `접수` 한 줄(`received()`)을 같이 넣어요 | 구현됨 (SCRUM-29) |
| 취소 때 결제 상태 | 윤강 | 관리자 취소 때 `payment.status`를 `결제취소`로 (값: 결제완료 · 결제취소) | 합의됨 |
| 재고 복구 | 박진 (SCRUM-21) | `ProductRepository.get_for_update` → `increase_stock` → `save_stock` | 합의됨 |
| camelCase · Page 형식 | 팀 전체 | 공통 `presentation/schemas.py`의 `CamelModel` · `Page[T]` (PR #15) | 합의됨 |
| 화면용 주문번호 | 윤강 · 박진 | 지금은 정수 `orderId`. 화면에 `G20261023-0001` 같은 번호가 필요하면 컬럼 추가 | 미정 |
