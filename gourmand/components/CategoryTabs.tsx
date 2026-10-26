import Link from "next/link";

import { CATEGORIES } from "@/lib/categories";
import { fetchCategoryCounts } from "@/lib/products";

// 카테고리 페이지 상단의 카테고리 전환 탭 (현재 카테고리는 브라운으로 강조)
// 상품 수는 API 에서 받아요 (Suspense 안에서 써 주세요)
export default async function CategoryTabs({ active }: { active: string }) {
  const counts = await fetchCategoryCounts();
  return (
    <nav
      aria-label="카테고리 선택"
      className="flex flex-wrap gap-2"
    >
      {CATEGORIES.map((c) => {
        const isActive = c.slug === active;
        return (
          <Link
            key={c.slug}
            href={`/category/${c.slug}`}
            aria-current={isActive ? "page" : undefined}
            className={`flex h-10 items-center gap-1.5 rounded-full border pl-1.5 pr-3 text-[13px] font-bold transition md:h-12 md:gap-2 md:pl-2 md:pr-4 md:text-[15px] ${
              isActive
                ? "border-brand bg-brand text-white"
                : "border-gray-200 bg-white text-gray-700 hover:border-brand-line hover:bg-brand-soft"
            }`}
          >
            <img src={c.image} alt="" className="h-6 w-6 rounded-full bg-white object-contain md:h-7 md:w-7" />
            {c.name}
            <span className="font-medium opacity-80">{counts[c.slug] ?? 0}</span>
          </Link>
        );
      })}
    </nav>
  );
}
