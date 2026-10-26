export type OrderInput = {
  buyerName: string;
  phone: string;
  zipcode: string;
  address1: string;
  address2: string;
};

// 주문 상태 (주문하면 "접수"로 시작해요)
export const ORDER_STATUSES = [
  "접수",
  "상품준비중",
  "배송중",
  "배송완료",
  "배송지연",
  "주문취소",
] as const;

// 예전에 이 브라우저(localStorage)에 저장하던 배송 정보 키. 같은 PC 의 다른 회원에게 보여서 계정(서버)으로 옮겼고,
// 남아 있는 값은 CartProvider 가 지워요
export const LEGACY_SHIPPING_KEY = "gourmand-shipping";
