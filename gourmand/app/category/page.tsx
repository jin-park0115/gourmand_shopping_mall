import { Suspense } from "react";
import Link from "next/link";

import { CATEGORIES } from "@/lib/categories";
import { COUNTRY_FILTERS, fetchCategoryCounts } from "@/lib/products";

export const metadata = { title: "카테고리 | 구르망" };

// 카테고리 카드 (상품 수는 API 에서)
async function CategoryCards() {
  const counts = await fetchCategoryCounts();
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);

  return (
    <>
      <p className="mb-4 mt-1 text-sm text-[#6E5B50]">어떤 간식이 당기세요? 전체 {total}개</p>

      <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3 md:gap-4">
        {CATEGORIES.map((c) => (
          <Link
            key={c.slug}
            href={`/category/${c.slug}`}
            className="flex items-center gap-3 rounded-2xl border border-brand-line bg-brand-soft px-3 py-2.5 text-[#2A1A12] transition hover:border-brand md:px-5 md:py-4"
          >
            <span className="flex h-[60px] w-[60px] flex-none items-center justify-center overflow-hidden rounded-[14px] bg-white md:h-20 md:w-20">
              <img src={c.image} alt="" className="h-[54px] w-[54px] object-contain md:h-[72px] md:w-[72px]" />
            </span>
            <span className="flex min-w-0 flex-col">
              <span className="break-keep text-[15px] font-extrabold leading-tight md:text-lg">{c.name}</span>
              <span className="hidden break-keep text-sm text-[#6E5B50] md:block">{c.desc}</span>
              <span className="text-xs font-bold text-brand md:mt-1">{counts[c.slug] ?? 0}개</span>
            </span>
          </Link>
        ))}
      </div>
    </>
  );
}

// 전체 카테고리 (모바일 하단 '카테고리' 탭, 홈의 '전체 카테고리')
export default function CategoryIndexPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:py-8">
      <h1 className="text-2xl font-extrabold text-[#2A1A12]">카테고리</h1>
      <Suspense fallback={<p className="mb-4 mt-1 text-sm text-[#6E5B50]">카테고리를 불러오는 중이에요…</p>}>
        <CategoryCards />
      </Suspense>

      <h2 className="mb-2.5 mt-8 text-base font-extrabold text-[#2A1A12]">나라별로 보기</h2>
      <div className="flex flex-wrap gap-1.5">
        {COUNTRY_FILTERS.map((c) => (
          <Link
            key={c.slug}
            href={`/country/${c.slug}`}
            className="inline-flex h-10 items-center rounded-full border border-gray-200 px-3.5 text-sm font-semibold text-gray-700 transition hover:border-brand-line hover:bg-brand-soft"
          >
            {c.name}
          </Link>
        ))}
      </div>
    </main>
  );
}
