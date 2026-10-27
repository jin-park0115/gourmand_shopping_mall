// 로딩 스켈레톤: 실제 화면 모양대로 회색 뼈대를 그려서, 데이터가 와도 화면이 덜컥 움직이지 않게 해요.
// 쉬머(빛이 지나가는 효과)는 globals.css 의 .skeleton 이 해요. 서버 · 클라이언트 어디서든 쓸 수 있어요.

type Props = { className?: string };

export function Bone({ className = "" }: Props) {
  return <div aria-hidden="true" className={`skeleton rounded-md ${className}`} />;
}

// 화면 읽기 프로그램에는 "불러오는 중"만 읽혀요
export function Loading({ label = "불러오는 중이에요", className = "", children }: { label?: string; className?: string; children: React.ReactNode }) {
  return (
    <div role="status" aria-busy="true" className={className}>
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

// ProductCard 와 같은 모양
export function ProductCardSkeleton() {
  return (
    <div>
      <Bone className="aspect-square w-full rounded-xl" />
      <div className="mt-3 space-y-2 px-1">
        <Bone className="h-4 w-4/5" />
        <Bone className="h-5 w-1/2" />
        <Bone className="h-3.5 w-1/3" />
      </div>
    </div>
  );
}

// 상품 목록 격자 (ProductResults · 나라 · 카테고리 · PICK)
export function ProductGridSkeleton({ count = 8, label = "상품을 불러오는 중이에요" }: { count?: number; label?: string }) {
  return (
    <Loading label={label}>
      <Bone className="mt-8 h-5 w-40" />
      <div className="mt-6 grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: count }, (_, i) => (
          <ProductCardSkeleton key={i} />
        ))}
      </div>
    </Loading>
  );
}

// 메인의 가로 줄 (HomeSection + ProductRow) 여러 개
export function HomeRowsSkeleton({ rows = 2 }: { rows?: number }) {
  return (
    <Loading label="상품을 불러오는 중이에요">
      {Array.from({ length: rows }, (_, r) => (
        <section key={r} className="mt-10">
          <Bone className="h-7 w-48" />
          <div className="mt-4 flex gap-4 overflow-hidden">
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="w-[44%] shrink-0 md:w-[31%] lg:w-[calc(25%-12px)]">
                <ProductCardSkeleton />
              </div>
            ))}
          </div>
        </section>
      ))}
    </Loading>
  );
}

// 상품 상세 (사진 | 정보)
export function ProductDetailSkeleton() {
  return (
    <Loading label="상품을 불러오는 중이에요">
      <Bone className="mb-5 h-4 w-56" />
      <div className="grid gap-8 lg:grid-cols-2 lg:gap-12">
        <Bone className="aspect-square w-full rounded-2xl" />
        <div className="space-y-4">
          <div className="flex gap-2">
            <Bone className="h-7 w-16 rounded-full" />
            <Bone className="h-7 w-20 rounded-full" />
          </div>
          <Bone className="h-8 w-4/5" />
          <Bone className="h-4 w-32" />
          <Bone className="h-9 w-48" />
          <Bone className="h-16 w-full" />
          <Bone className="h-28 w-full" />
          <Bone className="h-14 w-full rounded-xl" />
        </div>
      </div>
    </Loading>
  );
}

// 카드 목록 (리뷰 · 장바구니 · 주문 내역 · 관리자 주문 등)
export function ListSkeleton({ rows = 3, label, thumb = false, className = "" }: { rows?: number; label?: string; thumb?: boolean; className?: string }) {
  return (
    <Loading label={label} className={className}>
      <div className="space-y-4">
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="flex gap-4 rounded-xl border border-gray-100 p-4">
            {thumb && <Bone className="h-16 w-16 shrink-0 rounded-lg" />}
            <div className="flex-1 space-y-2.5">
              <Bone className="h-4 w-1/3" />
              <Bone className="h-4 w-full" />
              <Bone className="h-4 w-2/3" />
            </div>
          </div>
        ))}
      </div>
    </Loading>
  );
}
