import Link from "next/link";

import { CATEGORIES } from "@/lib/categories";
import { fetchCategoryCounts } from "@/lib/products";

// 홈: 나라 아이콘 아래 '어떤 간식이 당기세요?' 카테고리 줄
// 상품 수는 API 에서 받아요 (Suspense 안에서 써 주세요)
export default async function CategoryMenu() {
  const counts = await fetchCategoryCounts();
  return (
    <section
      aria-label="종류별 바로가기"
      className="rounded-2xl border border-brand-line bg-brand-soft px-4 pb-5 pt-5 md:px-7 md:pb-7 md:pt-6"
    >
      <div className="mb-4 flex items-end justify-between gap-3">
        <h2 className="text-lg font-extrabold text-[#2A1A12] md:text-[22px]">어떤 간식이 당기세요?</h2>
        <Link href="/category" className="shrink-0 text-sm font-bold text-brand hover:text-brand-dark">
          전체 카테고리 ›
        </Link>
      </div>

      {/* PC 6칸 · 태블릿 3칸 · 모바일 3칸(2줄) */}
      <div className="grid grid-cols-3 gap-2.5 md:gap-3.5 lg:grid-cols-6">
        {CATEGORIES.map((c) => (
          <Link
            key={c.slug}
            href={`/category/${c.slug}`}
            className="flex flex-col items-center gap-2 rounded-2xl border border-[#EADFD6] bg-white px-2 py-3 text-[#2A1A12] transition hover:-translate-y-0.5 hover:border-brand-line hover:shadow-sm md:gap-2.5 md:py-[18px]"
          >
            <span className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full border border-[#F1E8E0] bg-[#FBF8F5] md:h-[92px] md:w-[92px]">
              <img src={c.image} alt="" className="h-14 w-14 object-contain md:h-[82px] md:w-[82px]" />
            </span>
            <span className="break-keep text-center text-sm font-extrabold leading-tight md:text-base">{c.name}</span>
            <span className="hidden min-h-[34px] break-keep text-center text-xs leading-snug text-[#6E5B50] md:block">{c.desc}</span>
            <span className="rounded-full bg-brand-soft px-2.5 py-0.5 text-xs font-bold text-brand">
              {counts[c.slug] ?? 0}개
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
