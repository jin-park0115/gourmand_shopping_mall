# ERD (SCRUM-9)

> 기준: `develop` 의 `infrastructure/*/models.py` 와 `backend/migrations/versions` (2026-10-28)
> 테이블 12개. 처음 초안에서 C가 제안한 `orders` 배송 컬럼 · `order_status_history` · 인덱스는 모두 반영됐어요.

## 다이어그램

```mermaid
erDiagram
    country  ||--o{ product : "원산 국가"
    category ||--o{ product : "분류"
    product  ||--o{ review : "리뷰"
    member   ||--o{ review : "작성"
    member   ||--o{ address : "배송지"
    member   ||--o{ cart_item : "장바구니"
    product  ||--o{ cart_item : "담김"
    member   ||--o{ wishlist : "찜"
    product  ||--o{ wishlist : "찜됨"
    member   ||--o{ orders : "주문"
    orders   ||--|{ order_item : "주문 상품"
    product  ||--o{ order_item : "참조"
    orders   ||--o| payment : "결제"
    orders   ||--o{ order_status_history : "상태 이력"
    member   |o--o{ order_status_history : "변경한 사람"

    country {
        int country_id PK
        varchar name UK
        varchar slug UK "URL용 (japan 등), nullable"
    }
    category {
        int category_id PK
        varchar name UK
        varchar slug UK "URL용 (chocolate 등)"
    }
    product {
        int product_id PK
        int country_id FK
        int category_id FK
        varchar name
        varchar manufacturer
        text description
        int price
        int discount_price "nullable"
        varchar image_url
        bool is_new
        int stock "주문 시 차감, 취소 시 복구"
        int delivery_days
        numeric volume
        varchar unit
        int item_count
        varchar origin
        varchar food_type
        varchar storage_method
    }
    review {
        int review_id PK
        int product_id FK
        int member_id FK "작성자"
        int rating "1~5 (CHECK)"
        text content
        timestamp created_at
        timestamp updated_at "nullable"
    }
    member {
        int member_id PK
        varchar email UK
        varchar password_hash
        varchar name
        varchar phone "nullable"
        varchar role "customer | admin"
        timestamp created_at
    }
    address {
        int address_id PK
        int member_id FK
        varchar recipient
        varchar phone
        varchar zipcode
        varchar address1
        varchar address2 "nullable"
        bool is_default
    }
    cart_item {
        int member_id PK, FK
        int product_id PK, FK
        int quantity "1 이상 (CHECK)"
        timestamp added_at
    }
    wishlist {
        int member_id PK, FK
        int product_id PK, FK
        timestamp created_at
    }
    orders {
        int order_id PK
        int member_id FK
        varchar status "기본 접수"
        int total_price "0 이상 (CHECK)"
        varchar recipient
        varchar phone
        varchar zipcode
        varchar address1
        varchar address2 "nullable"
        timestamp ordered_at
        varchar courier "배송중부터 필수, nullable"
        varchar tracking_no "배송중부터 필수, nullable"
        varchar admin_note "지연 사유 등, nullable"
        timestamp updated_at
    }
    order_item {
        int order_item_id PK
        int order_id FK
        int product_id FK
        int quantity "1 이상 (CHECK)"
        int unit_price "주문 당시 가격, 0 이상 (CHECK)"
    }
    payment {
        int payment_id PK
        int order_id FK, UK
        varchar method
        int amount
        varchar status "결제완료 | 결제취소"
        timestamp paid_at "nullable"
    }
    order_status_history {
        int history_id PK
        int order_id FK
        varchar from_status "첫 접수는 null (CHECK)"
        varchar to_status "CHECK"
        int changed_by FK "member, 시스템이면 null"
        varchar note "nullable"
        timestamp changed_at
    }
    token_blacklist {
        varchar jti PK "로그아웃한 토큰 ID"
        timestamp expires_at "지나면 정리"
    }
```

`token_blacklist` 는 다른 테이블과 FK 없이 따로 있어요 (로그아웃 시 토큰 ID 기록, 인증할 때 확인).

## 제약 · 인덱스

| 대상 | 내용 |
| --- | --- |
| `order_status_history` | `from_status` · `to_status` 체크 제약 `IN ('접수','상품준비중','배송중','배송완료','배송지연','주문취소')`. 값은 `domain/order/status.py` · 프론트와 같아요 |
| `orders.status` | DB 체크 제약은 없고, 도메인(`ADMIN_TRANSITIONS`)에서 허용된 전이만 막아요 |
| 인덱스 | `orders (status, ordered_at)` 관리자 목록 필터 · `order_status_history (order_id, changed_at)` · `orders.member_id` · `order_item.order_id` · `order_item.product_id` · `address.member_id` · `token_blacklist.expires_at` |

## 상태 · 취소 규칙

- 관리자 상태 변경: 접수 → 상품준비중 → 배송중 → 배송완료 (배송중 ↔ 배송지연). 배송지연 · 주문취소는 사유 필수
- 취소 가능: `접수` · `상품준비중` 에서만 (관리자 · 고객 같음)
- 취소하면 `payment.status` 를 `결제취소` 로 바꾸고 `product.stock` 을 복구해요

## 트랜잭션 규칙

- **주문 생성 (B)**: `orders` + `order_item` + `payment` 저장, `product.stock` 차감, 주문한 상품만 `cart_item` 에서 빼기 (+ 배송지 저장 선택), 첫 이력(`null → 접수`)을 한 트랜잭션으로
- **관리자 상태 변경 · 취소 (C)**: 상태 변경 + 이력 기록 (+ 취소면 `payment` 결제취소 · `product.stock` 복구)을 한 트랜잭션으로. 같은 주문을 동시에 바꾸지 않게 `SELECT ... FOR UPDATE` 로 주문 행을 잠가요
