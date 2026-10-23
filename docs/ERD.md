# ERD (SCRUM-9)

> 기준: `develop` 의 `infrastructure/*/models.py` (SCRUM-8 ORM 모델 반영)
> **현재 모델 그대로** + **C(관리자 주문 운영)가 추가를 제안하는 부분**을 구분해서 적었어요. 제안 부분은 B·A와 합의 후 반영합니다.

## 다이어그램

```mermaid
erDiagram
    country  ||--o{ product : "원산 국가"
    category ||--o{ product : "분류"
    product  ||--o{ review : "리뷰"
    member   ||--o{ address : "배송지"
    member   ||--o{ cart_item : "장바구니"
    product  ||--o{ cart_item : "담김"
    member   ||--o{ wishlist : "찜"
    product  ||--o{ wishlist : "찜됨"
    member   ||--o{ orders : "주문"
    orders   ||--|{ order_item : "주문 상품"
    product  ||--o{ order_item : "참조"
    orders   ||--o| payment : "결제"
    orders   ||--o{ order_status_history : "상태 이력 (C 제안)"
    member   |o--o{ order_status_history : "변경한 사람 (C 제안)"

    country {
        int country_id PK
        varchar name UK
    }
    category {
        int category_id PK
        varchar name UK
    }
    product {
        int product_id PK
        int country_id FK
        int category_id FK
        varchar name
        int price
        int discount_price "nullable"
        int stock "주문 시 차감, 취소 시 복구"
    }
    review {
        int review_id PK
        int product_id FK
        varchar author_name
        int rating "1~5"
        text content
        timestamp created_at
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
        varchar zipcode
        bool is_default
    }
    cart_item {
        int member_id PK, FK
        int product_id PK, FK
        int quantity "1 이상"
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
        int total_price "0 이상"
        varchar recipient
        varchar phone
        varchar zipcode
        varchar address1
        varchar address2 "nullable"
        timestamp ordered_at
        varchar courier "C 제안: 배송중부터 필수"
        varchar tracking_no "C 제안: 배송중부터 필수"
        text admin_note "C 제안: 지연 사유 등"
        timestamp updated_at "C 제안"
    }
    order_item {
        int order_item_id PK
        int order_id FK
        int product_id FK
        int quantity "1 이상"
        int unit_price "주문 당시 가격"
    }
    payment {
        int payment_id PK
        int order_id FK, UK
        varchar method
        int amount
        varchar status
        timestamp paid_at "nullable"
    }
    order_status_history {
        int history_id PK
        int order_id FK
        varchar from_status "첫 접수는 null"
        varchar to_status
        int changed_by FK "member, 시스템이면 null"
        text note
        timestamp changed_at
    }
```

## C가 제안하는 변경 (합의 필요)

| 대상 | 변경 | 이유 | 관련 티켓 |
| --- | --- | --- | --- |
| `orders` | `courier`, `tracking_no` (nullable `String`) 추가 | 배송중으로 바꿀 때 택배사 · 운송장 필수 (관리자 화면에 이미 입력칸 있음) | SCRUM-35 |
| `orders` | `admin_note` (nullable `Text`) 추가 | 배송지연 사유 메모 (관리자 화면 `adminNote`) | SCRUM-35 |
| `orders` | `updated_at` 추가 | 마지막 상태 변경 시각 | SCRUM-35 |
| `orders` | `status` 에 체크 제약 `IN ('접수','상품준비중','배송중','배송완료','배송지연','주문취소')` | 잘못된 값 저장 방지. 값은 `domain/order/status.py` · 프론트와 동일 | SCRUM-32 |
| `order_status_history` | 신규 테이블 | 상태가 바뀔 때마다 한 줄 기록 (관리자 화면 이력 표시, 고객 취소도 기록) | SCRUM-33 |
| 인덱스 | `orders (status, ordered_at)` | 관리자 목록 상태 · 기간 필터 | SCRUM-34 |

`order_status_history` 는 C가 `infrastructure/admin/models.py` 에 만들어서 B의 `order/models.py` 파일과 겹치지 않게 할게요.
`orders` 컬럼 추가는 B 파일이라 **B가 추가하거나, C가 PR로 올리고 B가 리뷰**하는 방식 중 정해야 해요.

## 트랜잭션 규칙

- **주문 생성 (B)**: `orders` + `order_item` 저장, `product.stock` 차감, `cart_item` 비우기, 첫 이력(`null → 접수`)을 한 트랜잭션으로
- **관리자 상태 변경 · 취소 (C)**: 상태 변경 + 이력 기록 (+ 취소면 `product.stock` 복구)을 한 트랜잭션으로. 같은 주문을 동시에 바꾸지 않게 `SELECT ... FOR UPDATE` 로 주문 행을 잠가요

## 합의할 것

- [ ] 위 `orders` 컬럼 추가를 누가 반영할지
- [ ] 관리자 취소 가능 범위 — 제안: `접수`, `상품준비중` 에서만
- [ ] 취소 시 `payment.status` 를 함께 바꿀지 (예: `취소`)
