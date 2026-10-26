"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";

import { useAuth } from "@/components/AuthProvider";
import { api, ApiError, askLogin } from "@/lib/api";
import { LEGACY_SHIPPING_KEY } from "@/lib/orderStorage";

// 장바구니는 서버에 저장돼요 (SCRUM-27 /cart). 로그인한 회원만 쓸 수 있어요
export interface CartItem {
  id: number; // 상품 번호
  name: string;
  imageUrl: string;
  price: number; // 지금 판매가 (할인가가 있으면 할인가)
  quantity: number;
  stock: number; // 담을 수 있는 최대 수량
  isSoldOut: boolean; // 담아 둔 사이 품절됐는지
  subtotal: number;
}

interface CartResponse {
  items: CartItem[];
  totalCount: number;
  totalPrice: number;
}

const EMPTY: CartResponse = { items: [], totalCount: 0, totalPrice: 0 };

interface CartContextValue {
  items: CartItem[];
  hydrated: boolean; // 서버에서 불러오기가 끝났는지 (로그인 확인 포함)
  loadFailed: boolean; // 불러오지 못했는지 (빈 장바구니와 구분해서 안내)
  reload: () => void;
  orderable: boolean; // 품절 · 재고 초과 상품이 없어서 주문할 수 있는지
  totalCount: number;
  totalPrice: number;
  // 실패하면 ApiError 를 던져요 (예: 재고 초과 409). 화면은 error.message 를 그대로 보여 주면 돼요
  // 로그인하지 않았으면 로그인이 필요하다고 묻고(확인하면 로그인 화면으로) false 를 돌려줘요
  addItem: (productId: number, quantity?: number) => Promise<boolean>;
  setQuantity: (productId: number, quantity: number) => Promise<void>;
  removeItem: (productId: number) => Promise<void>;
  clearCart: () => Promise<void>;
}

const CartContext = createContext<CartContextValue | null>(null);

// 담아 둔 사이 품절되거나 재고가 줄면 그대로는 주문할 수 없어요
export function isOrderable(item: CartItem) {
  return !item.isSoldOut && item.quantity <= item.stock;
}
const LEGACY_STORAGE_KEY = "gourmand-cart"; // 예전 sessionStorage 장바구니 (SCRUM-28 전)

const json = (body: unknown): RequestInit => ({
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function CartProvider({ children }: { children: ReactNode }) {
  const { member, ready } = useAuth();
  // 누구의 장바구니인지 같이 저장해서, 로그인한 회원이 바뀌면 이전 회원 장바구니를 보여 주지 않아요
  const [loaded, setLoaded] = useState<{ memberId: number; cart: CartResponse; failed?: boolean } | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const memberId = member?.id ?? null;
  const cart = memberId !== null && loaded?.memberId === memberId ? loaded.cart : EMPTY;
  // 로그아웃 상태면 확인만 끝나면 되고, 로그인 상태면 그 회원 장바구니를 받아 와야 끝나요
  const hydrated = ready && (memberId === null || loaded?.memberId === memberId);

  // 로그인한 회원이 정해지면(또는 바뀌면) 서버에서 장바구니를 불러와요
  useEffect(() => {
    try {
      sessionStorage.removeItem(LEGACY_STORAGE_KEY);
      localStorage.removeItem(LEGACY_SHIPPING_KEY); // 브라우저에 남은 예전 배송 정보 (다른 회원에게 보이지 않게)
    } catch {
      // 지우지 못해도 더는 읽지 않아요
    }
    if (memberId === null) return;
    let cancelled = false;
    api<CartResponse>("/cart")
      .then((res) => ({ cart: res, failed: false }))
      .catch(() => ({ cart: EMPTY, failed: true })) // 서버가 꺼져 있어도 "비어 있어요"로 보이지 않게 따로 표시
      .then(({ cart, failed }) => {
        if (!cancelled) setLoaded({ memberId, cart, failed });
      });
    return () => {
      cancelled = true;
    };
  }, [memberId, reloadKey]);

  // 바뀐 뒤 장바구니 전체가 응답으로 와서 그대로 화면에 반영해요
  const mutate = useCallback(
    async (path: string, init: RequestInit) => {
      const res = await api<CartResponse>(path, init);
      if (memberId !== null) setLoaded({ memberId, cart: res });
    },
    [memberId]
  );

  const addItem: CartContextValue["addItem"] = async (productId, quantity = 1) => {
    if (!member) {
      askLogin(location.pathname + location.search);
      return false;
    }
    await mutate("/cart/items", { method: "POST", ...json({ productId, quantity }) });
    return true;
  };

  const setQuantity: CartContextValue["setQuantity"] = (productId, quantity) =>
    mutate(`/cart/items/${productId}`, { method: "PATCH", ...json({ quantity }) });

  const removeItem: CartContextValue["removeItem"] = (productId) =>
    mutate(`/cart/items/${productId}`, { method: "DELETE" });

  const clearCart: CartContextValue["clearCart"] = async () => {
    if (!member) return;
    await mutate("/cart", { method: "DELETE" });
  };

  return (
    <CartContext.Provider
      value={{
        items: cart.items,
        hydrated,
        loadFailed: memberId !== null && loaded?.memberId === memberId && !!loaded.failed,
        reload: () => setReloadKey((k) => k + 1),
        orderable: cart.items.every(isOrderable),
        totalCount: cart.totalCount,
        totalPrice: cart.totalPrice,
        addItem,
        setQuantity,
        removeItem,
        clearCart,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart는 CartProvider 안에서만 쓸 수 있어요.");
  return ctx;
}

// 화면에 보여 줄 오류 문구 (서버 메시지 우선)
export function cartErrorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "장바구니를 바꾸지 못했어요. 잠시 후 다시 시도해 주세요.";
}
