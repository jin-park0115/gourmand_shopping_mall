import Link from "next/link";

import type { Product } from "@/types/product";
import { CATEGORIES } from "@/lib/categories";

// 선택한 종류의 상품만 남기기 (종류를 고르지 않았거나 없는 값이면 전부)
export function filterByCategory(items: Product[], slug?: string) {
  if (!slug || !CATEGORIES.some((c) => c.slug === slug)) return items;
  return items.filter((p) => p.categorySlug === slug);
}

// 나라 페이지 · PICK 페이지 안에서 쓰는 과자 종류 필터
// (그 페이지 상품 중 해당 종류가 1개 이상 있을 때만 칩을 보여줘요)
export default function CategoryFilter({
  base,
  items,
  active,
}: {
  base: string; // 이 페이지 주소 (예: /country/japan)
  items: Product[]; // 이 페이지의 전체 상품
  active?: string; // 지금 고른 종류 slug
}) {
  const chips = CATEGORIES.map((c) => ({
    ...c,
    count: items.filter((p) => p.categorySlug === c.slug).length,
  })).filter((c) => c.count > 0);

  // 종류가 하나뿐이면 필터가 필요 없어요
  if (chips.length < 2) return null;

  const chipClass = (on: boolean) =>
    `inline-flex h-9 shrink-0 items-center gap-1 rounded-full border text-[13px] font-semibold transition md:h-10 md:gap-1.5 md:text-sm ${
      on
        ? "border-brand bg-brand text-white"
        : "border-gray-200 bg-white text-gray-700 hover:border-brand-line hover:bg-brand-soft"
    }`;

  return (
    <nav aria-label="과자 종류로 거르기" className="flex flex-wrap gap-1.5 md:gap-2">
      <Link
        href={`${base}#products`}
        scroll={false}
        aria-current={!active ? "true" : undefined}
        className={`${chipClass(!active)} px-3 md:px-4`}
      >
        전체 <span className="font-medium opacity-80">{items.length}</span>
      </Link>
      {chips.map((c) => (
        <Link
          key={c.slug}
          href={`${base}?category=${c.slug}#products`}
          scroll={false}
          aria-current={active === c.slug ? "true" : undefined}
          className={`${chipClass(active === c.slug)} pl-1 pr-2.5 md:pl-1.5 md:pr-3.5`}
        >
          <img src={c.image} alt="" className="h-6 w-6 rounded-full bg-white object-contain md:h-7 md:w-7" />
          {c.name}
          <span className="font-medium opacity-80">{c.count}</span>
        </Link>
      ))}
    </nav>
  );
}
