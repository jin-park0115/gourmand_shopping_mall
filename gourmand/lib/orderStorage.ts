export type OrderInput = {
  buyerName: string;
  phone: string;
  zipcode: string;
  address1: string;
  address2: string;
};

export type OrderLine = {
  id: number;
  name: string;
  imageUrl: string;
  price: number;
  quantity: number;
};

export type Order = {
  orderId: string;
  status: string;
  orderedAt: string;
  totalPrice: number;
  buyer: OrderInput;
  items: OrderLine[];
  // ── 관리자 페이지에서 채우는 항목 (없어도 동작해요) ──
  courier?: string; // 택배사
  trackingNo?: string; // 운송장 번호
  history?: { status: string; at: string }[]; // 상태가 바뀐 기록
  adminNote?: string; // 관리자 메모 (지연 사유 등)
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

const ORDERS_KEY = "gourmand-orders"; // 예전 브라우저 주문 내역 (마이페이지는 SCRUM-31 에서 주문 API 로 바꿔요)
const SHIPPING_KEY = "gourmand-shipping"; // 저장된 배송 정보

// 최신 주문이 앞에 오도록 저장되어 있어요.
export function getOrders(): Order[] {
  try {
    const raw = localStorage.getItem(ORDERS_KEY);
    return raw ? (JSON.parse(raw) as Order[]) : [];
  } catch {
    return [];
  }
}

export function saveShipping(input: OrderInput) {
  try {
    localStorage.setItem(SHIPPING_KEY, JSON.stringify(input));
  } catch {}
}

export function getSavedShipping(): OrderInput | null {
  try {
    const raw = localStorage.getItem(SHIPPING_KEY);
    return raw ? (JSON.parse(raw) as OrderInput) : null;
  } catch {
    return null;
  }
}

// 관리자 페이지: 주문 한 건의 상태 · 운송장 등을 바꿔서 저장해요.
// 마이페이지는 같은 저장소를 읽기 때문에 바뀐 상태가 그대로 보여요.
export function updateOrder(orderId: string, patch: Partial<Order>): Order[] {
  const orders = getOrders().map((o) =>
    o.orderId === orderId ? { ...o, ...patch } : o
  );
  try {
    localStorage.setItem(ORDERS_KEY, JSON.stringify(orders));
  } catch {}
  return orders;
}
