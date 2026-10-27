"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { cartErrorMessage, useCart } from "@/components/CartProvider";
import { Product } from "@/types/product";

// 상세 페이지의 수량 선택 + 장바구니 담기 (담으면 '장바구니로 이동할까요?' 창)
export default function ProductPurchase({
  p,
  price,
  soldOut,
}: {
  p: Product;
  price: number;
  soldOut: boolean;
}) {
  const router = useRouter();
  const { addItem, items } = useCart();
  const [quantity, setQuantity] = useState(1);
  const [addedQuantity, setAddedQuantity] = useState(0); // 창에 보여 줄 방금 담은 수량
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // 브라우저 기본 모달: Esc 로 닫기 · 창 밖 포커스 막기 · 배경 어둡게를 알아서 해 줘요
  const dialog = useRef<HTMLDialogElement>(null);

  // 이미 장바구니에 있는 수량까지 고려해서 최대 수량 제한
  const inCart = items.find((i) => i.id === p.id)?.quantity ?? 0;
  const maxQuantity = Math.max(0, p.stock - inCart);
  const reachedLimit = maxQuantity === 0;

  async function handleAdd() {
    setBusy(true);
    setError(null);
    try {
      // 로그인하지 않았으면 로그인 안내 창을 띄워요 (false)
      if (await addItem(p.id, quantity)) {
        setAddedQuantity(quantity);
        setQuantity(1);
        dialog.current?.showModal();
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

      {/* 실패 이유 */}
      <div aria-live="polite">{error && <p className="mt-3 text-sm text-red-500">{error}</p>}</div>

      {/* 담은 뒤: 장바구니로 갈지 묻기. 창 밖(어두운 배경)을 눌러도 닫혀요 */}
      <dialog
        ref={dialog}
        aria-labelledby="cart-added-title"
        onClick={(e) => e.target === e.currentTarget && dialog.current?.close()}
        className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-2xl p-0 shadow-xl backdrop:bg-black/40"
      >
        <div className="p-6 text-center">
          <p id="cart-added-title" className="text-lg font-bold text-gray-900">
            장바구니에 담았어요 ✓
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {p.name} · {addedQuantity}개
          </p>
          <p className="mt-4 text-sm text-gray-700">장바구니로 이동할까요?</p>
          <div className="mt-5 grid grid-cols-2 gap-2">
            <button
              type="button"
              autoFocus
              onClick={() => dialog.current?.close()}
              className="rounded-xl border border-gray-300 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
            >
              쇼핑 계속하기
            </button>
            <button
              type="button"
              onClick={() => {
                dialog.current?.close();
                router.push("/cart");
              }}
              className="rounded-xl bg-brand py-3 text-sm font-bold text-white transition hover:bg-brand-dark"
            >
              장바구니로 이동
            </button>
          </div>
        </div>
      </dialog>
    </div>
  );
}
