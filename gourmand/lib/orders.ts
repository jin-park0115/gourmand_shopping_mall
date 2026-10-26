// 주문 API (백엔드 /orders, SCRUM-29). 주문 상품 · 가격은 서버 장바구니에서 정해져서 배송 정보만 보내요
import { api, ApiError, type Page } from "@/lib/api";
import type { OrderInput } from "@/lib/orderStorage";

export interface OrderItem {
  productId: number;
  name: string;
  imageUrl: string;
  unitPrice: number; // 주문 당시 판매가
  quantity: number;
  subtotal: number;
}

export interface Order {
  orderId: number;
  status: string;
  orderedAt: string; // KST (시간대 표시 없음)
  totalPrice: number;
  recipient: string;
  phone: string;
  zipcode: string;
  address1: string;
  address2: string | null;
  items: OrderItem[];
  payment: { method: string; amount: number; status: string; paidAt: string | null } | null;
}

export function placeOrder(input: OrderInput) {
  return api<Order>("/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      recipient: input.buyerName,
      phone: input.phone,
      zipcode: input.zipcode,
      address1: input.address1,
      address2: input.address2 || null,
    }),
  });
}

export const fetchOrder = (orderId: number) => api<Order>(`/orders/${orderId}`);

export interface MyOrderFilter {
  status?: string; // 주문 상태 (없으면 전체)
  from?: string; // YYYY-MM-DD
  page?: number;
  size?: number;
}

export function fetchMyOrders({ status, from, page = 1, size = 5 }: MyOrderFilter) {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  if (status) params.set("status", status);
  if (from) params.set("from", from);
  return api<Page<Order>>(`/orders?${params}`);
}

// 접수 · 상품준비중일 때만 취소할 수 있어요 (서버 domain/order/status.py CUSTOMER_CANCELLABLE 과 같게)
export const CANCELLABLE_STATUSES = ["접수", "상품준비중"];

export const cancelOrder = (orderId: number) => api<Order>(`/orders/${orderId}/cancel`, { method: "POST" });

// 서버의 배송 정보 검증 문구를 해당 입력칸 아래에 보여 주려고 칸을 찾아요 (domain/order/order.py ShippingInfo 문구)
const FIELD_BY_MESSAGE: [string, keyof OrderInput][] = [
  ["받는 분", "buyerName"],
  ["휴대폰", "phone"],
  ["우편번호", "zipcode"],
  ["주소", "address1"],
];

export function shippingErrorField(error: unknown): keyof OrderInput | null {
  if (!(error instanceof ApiError) || error.code !== "INVALID_VALUE") return null;
  return FIELD_BY_MESSAGE.find(([word]) => error.message.startsWith(word))?.[1] ?? null;
}
