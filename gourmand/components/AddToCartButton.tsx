"use client";

import { useEffect, useRef, useState } from "react";
import { cartErrorMessage, useCart } from "@/components/CartProvider";
import { ApiError } from "@/lib/api";
import { Product } from "@/types/product";
import { isSoldOut } from "@/lib/products";

// 장바구니 아이콘
function CartIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      viewBox="0 0 24 24"
    >
      <path d="M3 4h2l2.2 10.2a1.5 1.5 0 0 0 1.5 1.2h8.6a1.5 1.5 0 0 0 1.5-1.1L20.5 8H6.2" />
      <circle cx="9.5" cy="19.5" r="1.3" />
      <circle cx="17" cy="19.5" r="1.3" />
    </svg>
  );
}

// 체크 아이콘 (담은 직후)
function CheckIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      viewBox="0 0 24 24"
    >
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
  );
}

// 상품 이미지 오른쪽 아래에 올라가는 동그란 장바구니 버튼
export default function AddToCartButton({ p }: { p: Product }) {
  const { addItem } = useCart();
  const [added, setAdded] = useState(false);
  const [error, setError] = useState<{ short: string; full: string } | null>(null);
  const [busy, setBusy] = useState(false);
  // 말풍선을 숨기는 타이머: 연달아 누르면 이전 타이머가 새 말풍선을 일찍 지우지 않게 매번 정리해요
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    []
  );

  function flash(next: { added: boolean; error: { short: string; full: string } | null }, ms: number) {
    if (timer.current) clearTimeout(timer.current);
    setAdded(next.added);
    setError(next.error);
    timer.current = setTimeout(() => {
      setAdded(false);
      setError(null);
    }, ms);
  }

  // 품절이면 버튼을 보여주지 않음 (이미지 위 '품절' 표시로 충분)
  if (isSoldOut(p)) return null;

  async function handleClick() {
    setBusy(true);
    try {
      // 로그인하지 않았으면 로그인 안내 창을 띄워요 (false)
      if (await addItem(p.id)) flash({ added: true, error: null }, 1500);
    } catch (e) {
      // 카드는 좁아서 짧게 보여 주고, 서버의 자세한 문구(예: 최대 2개)는 title · 화면 읽기 프로그램으로
      const short = e instanceof ApiError && e.status === 409 ? "더 담을 수 없어요" : "담지 못했어요";
      flash({ added: false, error: { short, full: cartErrorMessage(e) } }, 2500);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="absolute bottom-2 right-2 z-10 flex items-center gap-1.5">
      {/* 담은 직후 잠깐 보이는 말풍선 (화면 읽기 프로그램에도 안내) */}
      <span
        aria-live="polite"
        title={error?.full}
        className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold text-white shadow transition-opacity duration-200 ${
          error ? "bg-red-500" : "bg-brand"
        } ${added || error ? "opacity-100" : "pointer-events-none opacity-0"}`}
      >
        {error ? (
          <>
            {error.short}
            <span className="sr-only"> {error.full}</span>
          </>
        ) : added ? (
          "담았어요"
        ) : (
          ""
        )}
      </span>

      <button
        type="button"
        onClick={handleClick}
        disabled={busy}
        aria-label={`${p.name} 장바구니 담기`}
        title="장바구니 담기"
        className={`flex h-10 w-10 items-center justify-center rounded-full border shadow-md transition active:scale-95 ${
          added
            ? "border-brand bg-brand text-white"
            : "border-brand-line bg-white/95 text-brand hover:border-brand hover:bg-brand hover:text-white"
        }`}
      >
        {added ? <CheckIcon /> : <CartIcon />}
      </button>
    </div>
  );
}
