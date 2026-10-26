import { Suspense } from "react";
import OrderComplete from "@/components/OrderComplete";

export const metadata = { title: "주문 완료 | 구르망" };

export default function OrderCompletePage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      {/* 주소의 ?orderId= 를 읽어서(useSearchParams) Suspense 로 감싸요 */}
      <Suspense fallback={<p className="py-20 text-center text-gray-500">불러오는 중...</p>}>
        <OrderComplete />
      </Suspense>
    </main>
  );
}