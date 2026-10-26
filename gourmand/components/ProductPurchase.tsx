"use client";

import { useState } from "react";
import Link from "next/link";

import { cartErrorMessage, useCart } from "@/components/CartProvider";
import { Product } from "@/types/product";

// 상세 페이지의 수량 선택 + 장바구니 담기
export default function ProductPurchase({
  p,
  price,
  soldOut,
}: {
  p: Product;
  price: number;
  soldOut: boolean;
}) {
  const { addItem, items } = useCart();
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // 이미 장바구니에 있는 수량까지 고려해서 최대 수량 제한
  const inCart = items.find((i) => i.id === p.id)?.quantity ?? 0;
  const maxQuantity = Math.max(0, p.stock - inCart);
  const reachedLimit = maxQuantity === 0;

  async function handleAdd() {
    setBusy(true);
    setError(null);
    setAdded(false);
    try {
      // 로그인하지 않았으면 로그인 안내 창을 띄워요 (false)
      if (await addItem(p.id, quantity)) {
        setAdded(true);
        setQuantity(1);
      }
    } catch (e) {
      setError(cartErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  if (soldOut) {
    return (
      <button
        type="button"
        disabled
        className="w-full rounded-xl bg-gray-200 py-4 text-base font-bold text-gray-500"
      >
        품절된 상품이에요
      </button>
    );
  }

  return (
    <div>
      {/* 수량 + 합계 */}
      <div className="flex items-center justify-between rounded-xl bg-gray-50 px-4 py-3">
        <div className="flex items-center rounded-lg border border-gray-300 bg-white">
          <button
            type="button"
            onClick={() => setQuantity((q) => Math.max(1, q - 1))}
            disabled={quantity <= 1}
            aria-label="수량 줄이기"
            className="h-9 w-9 text-lg text-gray-700 disabled:text-gray-300"
          >
            −
          </button>
          <span aria-live="polite" className="min-w-10 text-center font-semibold">
            {quantity}
          </span>
          <button
            type="button"
            onClick={() => setQuantity((q) => Math.min(maxQuantity, q + 1))}
            disabled={quantity >= maxQuantity}
            aria-label="수량 늘리기"
            className="h-9 w-9 text-lg text-gray-700 disabled:text-gray-300"
          >
            +
          </button>
        </div>
        <p className="text-right">
          <span className="text-sm text-gray-500">총 상품금액 </span>
          <strong className="text-xl font-bold text-gray-900">
            {(price * quantity).toLocaleString()}원
          </strong>
        </p>
      </div>

      {reachedLimit && (
        <p className="mt-2 text-sm text-red-500">
          재고({p.stock}개)만큼 이미 장바구니에 담았어요.
        </p>
      )}

      <button
        type="button"
        onClick={handleAdd}
        disabled={reachedLimit || busy}
        className="mt-3 w-full rounded-xl bg-brand py-4 text-base font-bold text-white transition hover:bg-brand-dark active:scale-[0.99] disabled:bg-gray-300"
      >
        장바구니 담기
      </button>

      {/* 담은 뒤 안내 · 실패 이유 */}
      <div aria-live="polite">
        {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
        {added && (
          <div className="mt-3 flex items-center justify-between rounded-xl border border-brand-line bg-brand-soft px-4 py-3 text-sm">
            <span className="font-semibold text-brand">장바구니에 담았어요 ✓</span>
            <Link href="/cart" className="font-bold text-brand underline-offset-2 hover:underline">
              장바구니 보기 ›
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
