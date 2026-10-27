import { Suspense } from "react";

import ProductResults from "@/components/ProductResults";
import { ProductGridSkeleton } from "@/components/Skeletons";
import { firstParams } from "@/lib/params";

type ProductsPageProps = {
  searchParams: Promise<{
    q?: string;
    country?: string;
    category?: string;
    sort?: string;
  }>;
};

// 주소의 검색 조건(?q=...&country=...)을 읽는 부분 (Suspense 안에서 실행)
async function Results({ searchParams }: ProductsPageProps) {
  const { q, country, category, sort } = firstParams(await searchParams, "q", "country", "category", "sort");
  const keyword = q?.trim() || undefined;

  return (
    <>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        {keyword ? "검색 결과" : "전체 상품"}
      </h1>
      <ProductResults
        base="/products"
        query={{ q: keyword, country, category, sort }}
      />
    </>
  );
}

// 전체 상품 · 검색 결과 페이지 (헤더 검색창, 모바일 '카테고리' 탭)
export default function ProductsPage({ searchParams }: ProductsPageProps) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:py-8">
      <Suspense
        fallback={<ProductGridSkeleton />}
      >
        <Results searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
