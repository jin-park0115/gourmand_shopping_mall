import { Suspense } from "react";
import Link from "next/link";

import { POPULAR_KEYWORDS } from "@/lib/products";
import ProductResults from "@/components/ProductResults";

type SearchPageProps = {
  searchParams: Promise<{
    q?: string;
    country?: string;
    category?: string;
    sort?: string;
  }>;
};

// 큰 검색창 (검색어가 없으면 바로 입력할 수 있게 자동 포커스)
function SearchForm({ defaultValue }: { defaultValue?: string }) {
  return (
    <form action="/search" role="search" className="flex gap-2">
      <input
        key={defaultValue}
        type="search"
        name="q"
        defaultValue={defaultValue}
        autoFocus={!defaultValue}
        aria-label="간식 검색"
        placeholder="상품명, 나라, 브랜드, 초성(ㄱㅇㅈㄹ)으로 찾아보세요"
        className="h-12 min-w-0 flex-1 rounded-xl border border-brand-line bg-brand-soft px-4 text-base text-gray-900 outline-none transition placeholder:text-gray-500 focus:border-brand focus:bg-white focus:ring-2 focus:ring-brand-soft"
      />
      <button
        type="submit"
        className="h-12 shrink-0 rounded-xl bg-brand px-5 font-semibold text-white transition hover:bg-brand-dark"
      >
        검색
      </button>
    </form>
  );
}

async function SearchContent({ searchParams }: SearchPageProps) {
  const { q, country, category, sort } = await searchParams;
  const keyword = q?.trim() || undefined;

  return (
    <>
      <SearchForm defaultValue={keyword} />

      {keyword ? (
        <div className="mt-8">
          <ProductResults
            base="/search"
            query={{ q: keyword, country, category, sort }}
          />
        </div>
      ) : (
        // 검색 전: 추천 검색어
        <section className="mt-10">
          <h2 className="text-base font-bold text-gray-900">추천 검색어</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {POPULAR_KEYWORDS.map((word, index) => (
              <Link
                key={word}
                href={`/search?q=${encodeURIComponent(word)}`}
                className="flex items-center gap-1.5 rounded-full border border-gray-200 px-3.5 py-2 text-sm font-medium text-gray-700 transition hover:border-brand-line hover:bg-brand-soft hover:text-brand"
              >
                <span className="font-bold text-brand">{index + 1}</span>
                {word}
              </Link>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

// 검색 페이지 (모바일 하단 '검색' 탭)
export default function SearchPage({ searchParams }: SearchPageProps) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:py-8">
      <h1 className="sr-only">간식 검색</h1>
      <Suspense fallback={<SearchForm />}>
        <SearchContent searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
