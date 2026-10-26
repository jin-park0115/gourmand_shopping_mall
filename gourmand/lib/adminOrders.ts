// 관리자 주문 API (백엔드 /admin/orders, SCRUM-34 · 35). 관리자 토큰이 있어야 해요 (없으면 401, 고객이면 403)
// 응답 모양은 docs/API.md 'C 관리자 주문'과 같아요.
import { api, type Page } from "@/lib/api";
import { ORDER_STATUSES } from "@/lib/orderStorage";

export type OrderStatus = (typeof ORDER_STATUSES)[number];

export interface AdminOrder {
  orderId: number;
  status: OrderStatus;
  orderedAt: string;
  totalPrice: number;
  buyer: { buyerName: string; phone: string; zipcode: string; address1: string; address2: string | null };
  items: { id: number; name: string; imageUrl: string; price: number; quantity: number }[];
  courier: string | null;
  trackingNo: string | null;
  adminNote: string | null;
  nextStatuses: OrderStatus[]; // 지금 바꿀 수 있는 상태. 처리 버튼을 이 값으로 보여 줘요
  history: { status: OrderStatus; at: string; note: string | null }[] | null; // 상세 · 상태 변경 응답에만 있어요
}

export interface OrderSummary {
  total: number;
  statusCounts: Record<OrderStatus, number>;
  todayOrders: number;
  todaySales: number; // 오늘 주문 중 취소 제외
  todayUnits: number;
  waitingShipment: number; // 접수 + 상품준비중
  topProducts: { id: number; name: string; imageUrl: string; units: number }[];
}

export interface StatusChange {
  status: OrderStatus;
  courier?: string;
  trackingNo?: string;
  note?: string; // 배송지연 · 주문취소 사유
}

// 관리자 화면의 택배사 선택지 (백엔드 도메인 COURIERS 와 같아요)
export const COURIERS = ["CJ대한통운", "우체국택배", "한진택배", "롯데택배"];

// 빈 값은 빼고 쿼리스트링을 만들어요
function query(params: Record<string, string | number | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") qs.set(key, String(value));
  });
  const text = qs.toString();
  return text ? `?${text}` : "";
}

export const fetchAdminOrders = (params: { status?: OrderStatus; q?: string; page?: number; size?: number }) =>
  api<Page<AdminOrder>>(`/admin/orders${query(params)}`);

// 상태별 개수 · 전체 수 · TOP 5 는 검색어(q)를 따르고, 오늘 숫자는 늘 오늘 기준이에요
export const fetchOrderSummary = (q?: string) => api<OrderSummary>(`/admin/orders/summary${query({ q })}`);

export const fetchAdminOrder = (orderId: number) => api<AdminOrder>(`/admin/orders/${orderId}`);

export const changeOrderStatus = (orderId: number, body: StatusChange) =>
  api<AdminOrder>(`/admin/orders/${orderId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
