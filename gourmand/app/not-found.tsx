import { Suspense } from "react";
import Link from "next/link";
import type { Metadata } from "next";

import { COUNTRY_FILTERS, fetchProducts, isSoldOut } from "@/lib/products";

import ProductCard from "@/components/ProductCard";
import BackButton from "@/components/BackButton";
import { BittenCookie } from "@/components/CookieIllust";

export const metadata: Metadata = {
  title: "페이지를 찾을 수 없어요 | 구르망",
};

// 리뷰가 많은 순으로 인기 간식 4개 (품절 제외)
async function PopularProducts() {
  const popular = (await fetchProducts({ sort: "review" })).items.filter((p) => !isSoldOut(p)).slice(0, 4);
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-4">
      {popular.map((p) => (
        <ProductCard key={p.id} p={p} showCountry />
      ))}
    </div>
  );
}

// 잘못된 주소, 없는 상품·나라·PICK 주소로 들어왔을 때 보여주는 페이지 (404)
// notFound()를 부른 페이지도 모두 이 화면으로 와요
export default function NotFound() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:py-12">
      {/* 1. 안내 + 검색 + 이동 버튼 */}
      <section className="flex flex-col items-center rounded-3xl bg-brand-soft px-5 pb-8 pt-9 text-center md:px-6 md:pb-12 md:pt-14">
        <div
          role="img"
          aria-label="404"
          className="flex items-center gap-1 text-[68px] font-extrabold leading-none tracking-tight text-brand md:text-[104px]"
        >
          <span aria-hidden="true">4</span>
          <BittenCookie className="h-[68px] w-[68px] md:h-[104px] md:w-[104px]" />
          <span aria-hidden="true">4</span>
        </div>

        <p className="mt-4 text-[13px] font-bold text-[#c2185b] md:mt-6 md:text-sm">
          페이지를 찾을 수 없어요
        </p>
        <h1 className="mt-1.5 break-keep text-[22px] font-extrabold text-gray-900 md:mt-2 md:text-[32px]">
          앗, 이 간식은 구르망에 없어요
        </h1>
        <p className="mt-2.5 break-keep text-sm leading-relaxed text-[#6E5B50] md:mt-3 md:text-base">
          주소가 잘못 입력됐거나, 판매가 끝나 사라진 페이지예요.
          <span className="hidden md:inline">
            <br />
            대신 아래에서 다른 간식을 찾아보세요.
          </span>
        </p>

        <form action="/search" role="search" className="mt-5 flex w-full max-w-[480px] gap-2 md:mt-7">
          <label className="flex h-12 flex-1 items-center gap-2.5 rounded-full border-[1.5px] border-brand-line bg-white px-4 md:h-[52px] md:px-[18px]">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true" className="flex-none text-brand">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
            <input
              type="search"
              name="q"
              placeholder="어떤 간식을 찾으세요?"
              aria-label="간식 검색"
              className="w-full bg-transparent text-[15px] outline-none"
            />
          </label>
          <button
            type="submit"
            className="hidden h-[52px] rounded-full bg-brand px-[22px] text-[15px] font-bold text-white transition hover:bg-brand-dark md:block"
          >
            검색
          </button>
        </form>

        <div className="mt-3 grid w-full grid-cols-2 gap-2 md:mt-4 md:flex md:w-auto md:justify-center">
          <Link
            href="/"
            className="flex h-[46px] items-center justify-center rounded-full bg-brand px-[22px] text-[15px] font-bold text-white transition hover:bg-brand-dark md:border-[1.5px] md:border-brand md:bg-white md:text-brand md:hover:bg-brand-soft"
          >
            홈으로 가기
          </Link>
          <BackButton className="flex h-[46px] items-center justify-center rounded-full border-[1.5px] border-brand-line bg-white px-[22px] text-[15px] font-bold text-brand transition hover:border-brand md:border-transparent md:bg-transparent md:font-medium md:text-[#6E5B50] md:hover:text-brand" />
        </div>
      </section>

      {/* 2. 나라별로 둘러보기 */}
      <section className="mt-8 md:mt-12">
        <h2 className="mb-2.5 text-[17px] font-extrabold text-gray-900 md:mb-3.5 md:text-xl">나라별로 둘러보기</h2>
        <div className="flex flex-wrap gap-1.5 md:gap-2">
          {COUNTRY_FILTERS.map((c) => (
            <Link
              key={c.slug}
              href={`/country/${c.slug}`}
              className="inline-flex h-10 items-center rounded-full border border-gray-200 px-3.5 text-sm font-semibold text-gray-700 transition hover:border-brand-line hover:bg-brand-soft md:h-11 md:px-5 md:text-[15px]"
            >
              {c.name} 간식
            </Link>
          ))}
        </div>
      </section>

      {/* 3. 요즘 많이 찾는 간식 */}
      <section className="mt-8 md:mt-11">
        <div className="mb-3 flex items-baseline justify-between md:mb-3.5">
          <h2 className="text-[17px] font-extrabold text-gray-900 md:text-xl">요즘 많이 찾는 간식</h2>
          <Link href="/products" className="text-sm font-semibold text-brand hover:text-brand-dark">
            전체보기
          </Link>
        </div>
        <Suspense fallback={null}>
          <PopularProducts />
        </Suspense>
      </section>
    </main>
  );
}
