import { Suspense } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  COUNTRY_FILTERS,
  discountRate,
  fetchProduct,
  fetchProducts,
  hasDiscount,
  isSoldOut,
  salePrice,
} from "@/lib/products";

import HomeSection from "@/components/HomeSection";
import ProductCard from "@/components/ProductCard";
import ProductPurchase from "@/components/ProductPurchase";
import ProductReviews from "@/components/ProductReviews";
import ProductRow from "@/components/ProductRow";

type DetailPageProps = {
  params: Promise<{ id: string }>;
};

// 브라우저 탭 제목: "상품명 | 구르망"
export async function generateMetadata({ params }: DetailPageProps): Promise<Metadata> {
  const { id } = await params;
  const p = await fetchProduct(Number(id));
  return p
    ? { title: `${p.name} | 구르망 GOURMAND`, description: p.description }
    : { title: "구르망 GOURMAND" };
}

// 별점 (0~5점을 채운 별로 표시)
function Stars({ rating }: { rating: number }) {
  const percent = Math.max(0, Math.min(100, (rating / 5) * 100));
  return (
    <span aria-hidden="true" className="relative inline-block leading-none text-gray-300">
      ★★★★★
      <span
        className="absolute left-0 top-0 overflow-hidden whitespace-nowrap text-[#f5a623]"
        style={{ width: `${percent}%` }}
      >
        ★★★★★
      </span>
    </span>
  );
}

async function ProductDetail({ params }: DetailPageProps) {
  const { id } = await params;
  const p = await fetchProduct(Number(id));

  // 없는 상품(API 404) → app/not-found.tsx
  if (!p) notFound();

  const soldOut = isSoldOut(p);
  const price = salePrice(p);
  const countrySlug = p.countrySlug;
  const countryName =
    COUNTRY_FILTERS.find((c) => c.slug === countrySlug)?.name ?? p.country;

  // 같은 나라의 다른 간식 (서버 추천순: 품절은 뒤로, 평점 높은 순)
  const related = (await fetchProducts({ country: countrySlug })).items
    .filter((other) => other.id !== p.id)
    .slice(0, 8);

  // 상품 정보 표
  const infoRows = [
    { label: "식품유형", value: p.foodType },
    { label: "제조사", value: p.manufacturer },
    { label: "원산지", value: p.origin },
    {
      label: "내용량",
      value: `${p.volume}${p.unit}${p.itemCount > 1 ? ` × ${p.itemCount}개` : ""}`,
    },
    { label: "보관방법", value: p.storageMethod },
  ];

  return (
    <>
      {/* 위치 표시 */}
      <nav aria-label="현재 위치" className="mb-5 text-sm text-gray-500">
        <Link href="/" className="hover:text-brand">홈</Link>
        <span className="mx-1.5">›</span>
        <Link href={`/country/${countrySlug}`} className="hover:text-brand">
          {countryName} 간식
        </Link>
        <span className="mx-1.5">›</span>
        <span className="text-gray-700">{p.name}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-2 lg:gap-12">
        {/* 상품 이미지 */}
        <div className="relative aspect-square overflow-hidden rounded-2xl border border-gray-200 bg-white">
          <img src={p.imageUrl} alt={p.name} className="h-full w-full object-contain" />
          {p.isNew && (
            <span className="absolute left-3 top-3 rounded bg-brand px-2.5 py-1 text-xs font-bold text-white">
              NEW
            </span>
          )}
          {soldOut && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/70">
              <span className="rounded-full bg-gray-800 px-5 py-2 font-bold text-white">
                품절
              </span>
            </div>
          )}
        </div>

        {/* 상품 정보 */}
        <div className="flex flex-col">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Link
              href={`/country/${countrySlug}`}
              className="rounded-full bg-brand-soft px-3 py-1 font-semibold text-brand hover:bg-brand-line"
            >
              {p.country}
            </Link>
            <span className="rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-600">
              {p.category}
            </span>
          </div>

          <h1 className="mt-3 text-2xl font-bold leading-snug text-gray-900 md:text-[28px]">
            {p.name}
          </h1>

          <a href="#reviews" className="mt-2 flex w-fit items-center gap-1.5 text-sm hover:underline">
            <Stars rating={p.rating} />
            {p.reviewCount > 0 ? (
              <span className="text-gray-600">
                <strong className="font-semibold text-gray-900">{p.rating.toFixed(1)}</strong>{" "}
                · 리뷰 {p.reviewCount.toLocaleString()}개
              </span>
            ) : (
              <span className="text-gray-500">아직 리뷰가 없어요</span>
            )}
          </a>

          {/* 가격 */}
          <div className="mt-5 flex flex-wrap items-baseline gap-x-2">
            {hasDiscount(p) && (
              <span className="text-2xl font-bold text-accent">{discountRate(p)}%</span>
            )}
            <span className="text-3xl font-bold text-gray-900">
              {price.toLocaleString()}원
            </span>
            {hasDiscount(p) && (
              <span className="text-base text-gray-400 line-through">
                {p.price.toLocaleString()}원
              </span>
            )}
          </div>

          <p className="mt-5 leading-relaxed text-gray-600">{p.description}</p>

          {/* 배송 · 구성 요약 */}
          <dl className="mt-6 divide-y divide-gray-100 border-y border-gray-200 text-[15px]">
            <div className="flex gap-4 py-3">
              <dt className="w-20 shrink-0 text-gray-500">배송</dt>
              <dd className="font-semibold text-[#2f7d5b]">{p.deliveryDays}일 이내 도착</dd>
            </div>
            <div className="flex gap-4 py-3">
              <dt className="w-20 shrink-0 text-gray-500">내용량</dt>
              <dd className="text-gray-900">{infoRows[3].value}</dd>
            </div>
            <div className="flex gap-4 py-3">
              <dt className="w-20 shrink-0 text-gray-500">재고</dt>
              <dd className="text-gray-900">
                {soldOut ? "품절" : p.stock <= 10 ? `${p.stock}개 남았어요` : "넉넉해요"}
              </dd>
            </div>
          </dl>

          <div className="mt-6">
            <ProductPurchase p={p} price={price} soldOut={soldOut} />
          </div>
        </div>
      </div>

      {/* 상품 정보 고시 */}
      <section className="mt-14">
        <h2 className="text-xl font-bold text-gray-900">상품 정보</h2>
        <table className="mt-4 w-full border-t-2 border-gray-900 text-left text-[15px]">
          <tbody>
            {infoRows.map((row) => (
              <tr key={row.label} className="border-b border-gray-200">
                <th scope="row" className="w-28 bg-gray-50 px-4 py-3 font-medium text-gray-600 md:w-40">
                  {row.label}
                </th>
                <td className="px-4 py-3 text-gray-900">{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <ProductReviews productId={p.id} />

      {/* 같은 나라 간식 */}
      {related.length > 0 && (
        <HomeSection
          title={`${countryName} 간식 더 보기`}
          href={`/country/${countrySlug}`}
        >
          <ProductRow>
            {related.map((other) => (
              <ProductCard key={other.id} p={other} />
            ))}
          </ProductRow>
        </HomeSection>
      )}
    </>
  );
}

// 상품 상세 페이지 (/products/1)
export default function ProductDetailPage({ params }: DetailPageProps) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:py-8">
      <Suspense
        fallback={<p className="text-sm text-gray-500">상품을 불러오는 중이에요…</p>}
      >
        <ProductDetail params={params} />
      </Suspense>
    </main>
  );
}
