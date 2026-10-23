import Link from "next/link";
import { Product } from "@/types/product";
import { discountRate as rateOf, isSoldOut, salePrice as priceOf } from "@/lib/products";
import AddToCartButton from "@/components/AddToCartButton";

// showCountry: 여러 나라 상품이 섞인 목록(카테고리 페이지)에서 나라 표시
export default function ProductCard({ p, showCountry = false }: { p: Product; showCountry?: boolean }) {
  const salePrice = priceOf(p);
  const discountRate = rateOf(p);
  const hasDiscount = discountRate > 0;
  const soldOut = isSoldOut(p);

  // 별점 채움 비율 (0 ~ 100%)
  const ratingPercent = Math.max(0, Math.min(100, (p.rating / 5) * 100));

  return (
    <div className="group">
      {/* 이미지 + 장바구니 버튼 (버튼은 링크 밖에 두어 눌러도 상세로 이동하지 않음) */}
      <div className="relative">
        {/* 상세 페이지 경로는 팀에서 정한 라우트에 맞게 href만 바꾸세요 */}
        <Link
          href={`/products/${p.id}`}
          tabIndex={-1}
          aria-hidden="true"
          className="block"
        >
          <div className="relative aspect-square overflow-hidden rounded-xl border border-gray-200 bg-white">
            <img
              src={p.imageUrl}
              alt={p.name}
              className="h-full w-full object-contain transition duration-300 group-hover:scale-105"
            />

            <div className="absolute left-2 top-2 flex gap-1">
              {showCountry && (
                <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-bold text-gray-700">
                  {p.country}
                </span>
              )}
              {p.isNew && (
                <span className="rounded bg-brand px-2 py-0.5 text-[11px] font-bold text-white">
                  NEW
                </span>
              )}
            </div>

            {soldOut && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/70">
                <span className="rounded-full bg-gray-800 px-4 py-1.5 text-sm font-bold text-white">
                  품절
                </span>
              </div>
            )}
          </div>
        </Link>

        <AddToCartButton p={p} />
      </div>

      <Link href={`/products/${p.id}`} className="block">
        {/* 정보 */}
        <div className="mt-3 px-1">
          {/* 이름: 한 줄까지, 넘치면 ... */}
          <h3
            className={`line-clamp-1 text-[15px] font-semibold leading-[22px] ${
              soldOut ? "text-gray-400" : "text-gray-900"
            }`}
          >
            {p.name}
          </h3>

          {/* 가격 */}
          <div className="mt-1 flex flex-wrap items-baseline gap-x-1.5">
            {hasDiscount ? (
              <>
                <span className="text-[15px] font-bold text-accent">{discountRate}%</span>
                <span className="text-lg font-bold text-gray-900">
                  {salePrice?.toLocaleString()}원
                </span>
                <span className="text-xs text-gray-400 line-through">
                  {p.price.toLocaleString()}원
                </span>
              </>
            ) : (
              <span className="text-lg font-bold text-gray-900">
                {p.price.toLocaleString()}원
              </span>
            )}
          </div>

          {/* 배송 예상 */}
          <p className="mt-1 text-[13px] font-semibold text-[#2f7d5b]">
            {p.deliveryDays}일 이내 도착
          </p>

          {/* 별점 + 리뷰 수 */}
          <div className="mt-1 flex items-center gap-1">
            <span className="relative inline-block text-sm leading-none text-gray-300">
              ★★★★★
              <span
                className="absolute left-0 top-0 overflow-hidden whitespace-nowrap text-[#f5a623]"
                style={{ width: `${ratingPercent}%` }}
              >
                ★★★★★
              </span>
            </span>
            <span className="text-xs text-gray-500">({p.reviewCount.toLocaleString()})</span>
          </div>
        </div>
      </Link>
    </div>
  );
}