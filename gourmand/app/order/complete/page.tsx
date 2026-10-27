import { Suspense } from "react";
import OrderComplete from "@/components/OrderComplete";
import { ListSkeleton } from "@/components/Skeletons";

export const metadata = { title: "주문 완료 | 구르망" };

export default function OrderCompletePage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      {/* 주소의 ?orderId= 를 읽어서(useSearchParams) Suspense 로 감싸요 */}
      <Suspense fallback={<ListSkeleton rows={2} thumb label="주문 정보를 불러오는 중이에요" className="py-10" />}>
        <OrderComplete />
      </Suspense>
    </main>
  );
}