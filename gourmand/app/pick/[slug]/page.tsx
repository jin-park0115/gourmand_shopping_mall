import { Suspense } from "react";
import { notFound } from "next/navigation";

import { fetchProducts } from "@/lib/products";
import { picks } from "@/data/picks";

import CountryMenu from "@/components/CountryMenu";
import ProductCard from "@/components/ProductCard";
import CategoryFilter, { filterByCategory } from "@/components/CategoryFilter";

// params를 읽는 부분만 따로 분리 (Suspense 안에서 실행됨)
async function PickProducts({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ category?: string }>;
}) {
  const { slug } = await params;
  const { category } = await searchParams;
  const pick = picks[slug];

  // 없는 주소(/pick/abc)는 404
  if (!pick) notFound();

  // 픽에 정한 순서 그대로 보여 줘요 (서버는 추천순으로 돌려줘서 다시 맞춰요)
  const byId = new Map((await fetchProducts({ ids: pick.productIds })).items.map((p) => [p.id, p]));
  const pickProducts = pick.productIds.map((id) => byId.get(id)).filter((p) => p !== undefined);

  // 과자 종류로 거르기 (?category=snack)
  const shown = filterByCategory(pickProducts, category);

  return (
    <>
      <div className="mb-4 flex items-baseline gap-2">
        <h1 className="text-2xl font-bold">{pick.title}</h1>
        {pickProducts.length > 0 && (
          <span className="text-sm text-gray-500">{shown.length}개의 상품</span>
        )}
      </div>

      <div id="products" className="mb-6 scroll-mt-24">
        <CategoryFilter base={`/pick/${slug}`} items={pickProducts} active={category} />
      </div>

      {pickProducts.length === 0 ? (
        // 아직 고른 상품이 없을 때
        <p className="rounded-xl border border-gray-200 py-16 text-center text-gray-500">
          추천 상품을 고르는 중이에요. 곧 채워질 예정이에요!
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-3 lg:grid-cols-4">
          {shown.map((p) => (
            <ProductCard key={p.id} p={p} showCountry />
          ))}
        </div>
      )}
    </>
  );
}

export default function PickPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ category?: string }>;
}) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:py-8">
      {/* 나라별 바로가기 */}
      <section className="mt-6">
        <CountryMenu />
      </section>

      {/* pick 상품 (params를 읽는 부분만 Suspense) */}
      <section className="mt-10">
        <Suspense fallback={<p className="text-gray-500">불러오는 중...</p>}>
          <PickProducts params={params} searchParams={searchParams} />
        </Suspense>
      </section>
    </main>
  );
}