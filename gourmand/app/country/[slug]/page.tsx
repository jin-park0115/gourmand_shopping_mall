import { Suspense } from "react";
import Image from "next/image";
import { notFound } from "next/navigation";

import { fetchProducts } from "@/lib/products";

import CountryTabs from "@/components/CountryTabs";
import ProductCard from "@/components/ProductCard";
import CategoryFilter, { filterByCategory } from "@/components/CategoryFilter";

const countries: Record<string, { name: string; banner: string }> = {
  japan: { name: "일본", banner: "/images/banner-japan.png" },
  taiwan: { name: "대만", banner: "/images/banner-taiwan.png" },
  china: { name: "중국", banner: "/images/banner-china.png" },
  vietnam: { name: "베트남", banner: "/images/banner-vietnam.png" },
  other: { name: "그 외", banner: "/images/banner-global.png" },
};

type CountryPageProps = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ category?: string }>;
};

// 주소를 읽고 나라 배너 + 탭 + 상품 목록을 표시하는 부분
async function CountryContent({ params, searchParams }: CountryPageProps) {
  const { slug } = await params;
  const { category } = await searchParams;

  const country = countries[slug];

  if (!country) {
    notFound();
  }

  // 서버가 나라로 거르고 품절 상품은 뒤로 보내요 (other = 주요 4개국이 아닌 나라)
  const countryProducts = (await fetchProducts({ country: slug })).items;

  // 과자 종류로 거르기 (?category=snack)
  const shown = filterByCategory(countryProducts, category);

  return (
    <>
      {/* 1. 나라 전용 배너 */}
      {/* 배너 속 '지금 둘러보기'를 누르면 상품 목록으로 이동 */}
      <a
        href="#products"
        className="relative block aspect-[16/9] overflow-hidden rounded-2xl bg-brand-soft md:aspect-[3/1]"
      >
        <Image
          src={country.banner}
          alt={`${country.name} 과자 여행`}
          fill
          priority
          sizes="(max-width: 1152px) 100vw, 1152px"
          className="object-cover object-center"
        />
      </a>

      {/* 2. 나라 전환 탭 */}
      <div className="mt-5">
        <CountryTabs active={slug} />
      </div>

      {/* 3. 상품 목록 */}
      <section id="products" className="mt-8 scroll-mt-24">
        <div className="mb-6 flex items-baseline gap-2">
          <h1 className="text-2xl font-bold text-gray-900">
            {country.name} 간식
          </h1>
          <span className="text-sm text-gray-500">
            {shown.length}개의 상품
          </span>
        </div>

        <div className="mb-6">
          <CategoryFilter base={`/country/${slug}`} items={countryProducts} active={category} />
        </div>

        <div className="grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-3 lg:grid-cols-4">
          {shown.map((p) => (
            <ProductCard key={p.id} p={p} />
          ))}
        </div>
      </section>
    </>
  );
}

// 페이지 전체 배치
export default function CountryPage({ params, searchParams }: CountryPageProps) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:py-8">
      <Suspense
        fallback={
          <p className="text-sm text-gray-500">상품을 불러오는 중이에요…</p>
        }
      >
        <CountryContent params={params} searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
