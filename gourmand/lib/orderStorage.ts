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

const SHIPPING_KEY = "gourmand-shipping"; // 저장된 배송 정보

export function saveShipping(input: OrderInput) {
  try {
    localStorage.setItem(SHIPPING_KEY, JSON.stringify(input));
  } catch {}
}

// 화면이 렌더링 중에 읽을 수 있게 저장된 문자열 그대로 (useSyncExternalStore 용, 값이 같으면 같은 문자열)
export function savedShippingSnapshot(): string | null {
  try {
    return localStorage.getItem(SHIPPING_KEY);
  } catch {
    return null;
  }
}
