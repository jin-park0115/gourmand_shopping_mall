import Link from "next/link";

import { fetchProducts, ProductQuery, POPULAR_KEYWORDS } from "@/lib/products";

import ProductCard from "@/components/ProductCard";
import ProductFilters, { SortLinks } from "@/components/ProductFilters";

// 검색 결과 + 필터 + 정렬 (/products, /search 공통)
// 서버에서 검색해요 (Suspense 안에서 써 주세요)
export default async function ProductResults({
  base,
  query,
}: {
  base: string;
  query: ProductQuery;
}) {
  const results = (await fetchProducts(query)).items;
  const hasFilter = !!(query.country || query.category);

  return (
    <>
      <ProductFilters base={base} query={query} />

      <div className="mt-8 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-gray-200 pb-3">
        <p className="text-[15px] text-gray-700">
          {query.q && (
            <>
              <strong className="font-bold text-brand">‘{query.q}’</strong>{" "}
              검색 결과{" "}
            </>
          )}
          <strong className="font-bold text-gray-900">{results.length}</strong>개
        </p>
        <SortLinks base={base} query={query} />
      </div>

      {results.length > 0 ? (
        <div className="mt-6 grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-3 lg:grid-cols-4">
          {results.map((p) => (
            <ProductCard key={p.id} p={p} />
          ))}
        </div>
      ) : (
        // 결과가 없을 때: 다른 검색어 제안
        <div className="py-16 text-center">
          <p className="text-lg font-semibold text-gray-900">
            {query.q ? `‘${query.q}’에 맞는 간식을 찾지 못했어요` : "조건에 맞는 간식이 없어요"}
          </p>
          <p className="mt-2 text-sm text-gray-500">
            {hasFilter
              ? "나라나 종류 조건을 ‘전체’로 바꿔 보세요."
              : "다른 검색어로 찾아보세요."}
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {POPULAR_KEYWORDS.slice(0, 6).map((keyword) => (
              <Link
                key={keyword}
                href={`${base}?q=${encodeURIComponent(keyword)}`}
                className="rounded-full bg-brand-soft px-3.5 py-1.5 text-sm font-medium text-brand transition hover:bg-brand-line"
              >
                {keyword}
              </Link>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
