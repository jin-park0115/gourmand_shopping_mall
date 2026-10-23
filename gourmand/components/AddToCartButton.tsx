"use client";

import { useState } from "react";
import { useCart } from "@/components/CartProvider";
import { Product } from "@/types/product";
import { isSoldOut, salePrice } from "@/lib/products";

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

  const soldOut = isSoldOut(p);
  const price = salePrice(p);

  // 품절이면 버튼을 보여주지 않음 (이미지 위 '품절' 표시로 충분)
  if (soldOut) return null;

  function handleClick() {
    addItem({
      id: p.id,
      name: p.name,
      imageUrl: p.imageUrl,
      price,
      stock: p.stock,
    });
    setAdded(true);
    setTimeout(() => setAdded(false), 1500);
  }

  return (
    <div className="absolute bottom-2 right-2 z-10 flex items-center gap-1.5">
      {/* 담은 직후 잠깐 보이는 말풍선 (화면 읽기 프로그램에도 안내) */}
      <span
        aria-live="polite"
        className={`rounded-full bg-brand px-2.5 py-1 text-xs font-semibold text-white shadow transition-opacity duration-200 ${
          added ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      >
        {added ? "담았어요" : ""}
      </span>

      <button
        type="button"
        onClick={handleClick}
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
