import { Suspense } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCategory } from "@/lib/categories";
import { COUNTRY_FILTERS, fetchProducts } from "@/lib/products";

import CategoryTabs from "@/components/CategoryTabs";
import ProductCard from "@/components/ProductCard";
import { SortLinks } from "@/components/ProductFilters";
import { ProductGridSkeleton } from "@/components/Skeletons";
import { firstParams } from "@/lib/params";

type CategoryPageProps = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ country?: string; sort?: string }>;
};

export async function generateMetadata({ params }: Pick<CategoryPageProps, "params">): Promise<Metadata> {
  const { slug } = await params;
  const category = getCategory(slug);
  return { title: category ? `${category.name} | 구르망` : "구르망 GOURMAND" };
}

async function CategoryContent({ params, searchParams }: CategoryPageProps) {
  const { slug } = await params;
  const { country, sort } = firstParams(await searchParams, "country", "sort");

  const category = getCategory(slug);
  if (!category) notFound();

  // 카테고리 상품을 한 번 받아서(정렬은 서버) 나라 칩 개수 · 나라 필터는 여기서 계산해요
  const all = (await fetchProducts({ category: slug, sort })).items;
  const list = country ? all.filter((p) => p.countrySlug === country) : all;
  const base = `/category/${slug}`;

  // 나라 필터 칩 (상품이 있는 나라만)
  const countryChips = [
    { slug: undefined, name: "전체", count: all.length },
    ...COUNTRY_FILTERS.map((c) => ({
      slug: c.slug,
      name: c.name,
      count: all.filter((p) => p.countrySlug === c.slug).length,
    })).filter((c) => c.count > 0),
  ];
  const chipHref = (c?: string) => {
    const q = new URLSearchParams();
    if (c) q.set("country", c);
    if (sort && sort !== "recommend") q.set("sort", sort);
    const s = q.toString();
    return s ? `${base}?${s}` : base;
  };

  // 소개 영역에 겹쳐 놓을 대표 상품 사진 3장 (품절 제외)
  // (정렬을 바꿔도 사진이 바뀌지 않게 상품 번호 순)
  const heroImages = [...all].sort((a, b) => a.id - b.id).filter((p) => !p.isSoldOut && p.stock > 0).slice(0, 3);

  return (
    <>
      <nav aria-label="현재 위치" className="mb-3.5 text-sm text-gray-500">
        <Link href="/" className="hover:text-brand">홈</Link>
        <span className="mx-1.5">›</span>
        <Link href="/category" className="hover:text-brand">카테고리</Link>
        <span className="mx-1.5">›</span>
        <span className="text-gray-700">{category.name}</span>
      </nav>

      {/* 카테고리 소개 */}
      <section className="flex items-center justify-between gap-4 overflow-hidden rounded-[20px] border border-brand-line bg-brand-soft px-5 py-6 md:h-[200px] md:px-10 md:py-8">
        <div className="flex flex-col gap-1.5 md:gap-2">
          <span className="text-sm font-bold text-brand">구르망 카테고리</span>
          <h1 className="text-[28px] font-extrabold tracking-tight text-[#2A1A12] md:text-[40px]">{category.name}</h1>
          <p className="text-sm text-[#6E5B50] md:text-base">
            {category.desc} <strong className="text-[#2A1A12]">{all.length}개</strong>
          </p>
        </div>
        <div className="hidden items-end sm:flex">
          {heroImages.map((p, i) => (
            <img
              key={p.id}
              src={p.imageUrl}
              alt=""
              className={`object-contain mix-blend-multiply ${i === 1 ? "h-40 w-40" : "h-[140px] w-[140px]"} ${i < 2 ? "-mr-6" : ""}`}
            />
          ))}
        </div>
      </section>

      {/* 카테고리 탭 */}
      <div className="mt-5">
        <CategoryTabs active={slug} />
      </div>

      {/* 나라 필터 + 정렬 */}
      <section id="products" className="mt-7 scroll-mt-24">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-b border-gray-200 pb-3.5">
          <div className="-mx-4 flex items-center gap-2 overflow-x-auto px-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <span className="mr-1 shrink-0 text-sm font-bold text-gray-500">나라</span>
            {countryChips.map((c) => {
              const active = (country ?? undefined) === c.slug;
              return (
                <Link
                  key={c.name}
                  href={chipHref(c.slug)}
                  scroll={false}
                  aria-current={active ? "true" : undefined}
                  className={`inline-flex h-9 shrink-0 items-center rounded-full border px-3.5 text-sm font-semibold transition ${
                    active
                      ? "border-[#3E1A08] bg-[#3E1A08] text-white"
                      : "border-gray-200 bg-white text-gray-700 hover:border-brand-line hover:bg-brand-soft"
                  }`}
                >
                  {c.name} {c.count}
                </Link>
              );
            })}
          </div>
          <SortLinks base={base} query={{ country, sort }} />
        </div>

        {list.length > 0 ? (
          <div className="mt-6 grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-3 lg:grid-cols-4">
            {list.map((p) => (
              <ProductCard key={p.id} p={p} showCountry />
            ))}
          </div>
        ) : (
          <p className="py-16 text-center text-gray-500">이 나라의 {category.name} 상품은 아직 없어요.</p>
        )}
      </section>
    </>
  );
}

// 카테고리 페이지 (/category/snack 등)
export default function CategoryPage(props: CategoryPageProps) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:py-8">
      <Suspense fallback={<ProductGridSkeleton />}>
        <CategoryContent {...props} />
      </Suspense>
    </main>
  );
}
