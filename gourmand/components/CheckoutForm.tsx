"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCart } from "@/components/CartProvider";
import {
  createOrder,
  getSavedShipping,
  saveShipping,
  type OrderInput,
} from "@/lib/orderStorage";

type Errors = Partial<Record<keyof OrderInput, string>>;

// 시연용 미리 채워 둔 배송 정보 (시연이 끝나면 DEMO_PREFILL을 false로 바꾸면 빈칸으로 돌아가요)
const DEMO_PREFILL = true;

const DEMO_SHIPPING: OrderInput = {
  buyerName: "윤강",
  phone: "010-1223-4545",
  zipcode: "06236",
  address1: "서울특별시 강남구 테헤란로 123",
  address2: "구르망빌딩 3층",
};

const EMPTY: OrderInput = {
  buyerName: "",
  phone: "",
  zipcode: "",
  address1: "",
  address2: "",
};

const INITIAL: OrderInput = DEMO_PREFILL ? DEMO_SHIPPING : EMPTY;

function validate(form: OrderInput): Errors {
  const errors: Errors = {};
  if (!form.buyerName.trim()) errors.buyerName = "받는 분 이름을 입력해 주세요.";
  if (!/^01[0-9]-?\d{3,4}-?\d{4}$/.test(form.phone.trim()))
    errors.phone = "휴대폰 번호를 올바르게 입력해 주세요. (예: 010-1234-5678)";
  if (!/^\d{5}$/.test(form.zipcode.trim()))
    errors.zipcode = "우편번호 5자리를 입력해 주세요.";
  if (!form.address1.trim()) errors.address1 = "주소를 입력해 주세요.";
  return errors;
}

const inputClass =
  "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand";

export default function CheckoutForm() {
  const router = useRouter();
  const { items, hydrated, totalCount, totalPrice, clearCart, orderable } = useCart();
  const [form, setForm] = useState<OrderInput>(INITIAL);
  const [errors, setErrors] = useState<Errors>({});
  const [submitted, setSubmitted] = useState(false);
  const [saved, setSaved] = useState<OrderInput | null>(null);
  const [remember, setRemember] = useState(true);

  // 저장된 배송 정보가 있는지 확인 (브라우저에서만 가능해서 effect 안에서 읽어요)
  useEffect(() => {
    setSaved(getSavedShipping());
  }, []);

  if (!hydrated) {
    return <p className="py-20 text-center text-gray-500">불러오는 중...</p>;
  }

  // 주문 완료 직후 clearCart로 장바구니가 비어도 빈 화면 안내가 깜빡이지 않게 처리
  if (items.length === 0 && !submitted) {
    return (
      <div className="py-20 text-center">
        <p className="text-gray-600">장바구니가 비어 있어요.</p>
        <Link
          href="/"
          className="mt-4 inline-block rounded-lg bg-brand px-5 py-2.5 font-semibold text-white transition hover:bg-brand-dark"
        >
          쇼핑하러 가기
        </Link>
      </div>
    );
  }

  // 주소창으로 바로 들어와도 품절 · 재고 초과 상품은 주문하지 못하게 (서버 검증은 주문 API SCRUM-29)
  if (!orderable && !submitted) {
    return (
      <div className="py-20 text-center">
        <p className="text-gray-600">품절됐거나 재고보다 많이 담은 상품이 있어요. 장바구니에서 정리해 주세요.</p>
        <Link
          href="/cart"
          className="mt-4 inline-block rounded-lg bg-brand px-5 py-2.5 font-semibold text-white transition hover:bg-brand-dark"
        >
          장바구니로 가기
        </Link>
      </div>
    );
  }

  const handleChange =
    (key: keyof OrderInput) => (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [key]: e.target.value }));
      if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
    };

  const loadSaved = () => {
    if (!saved) return;
    setForm(saved);
    setErrors({});
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitted(true);
    createOrder(
      form,
      items.map((i) => ({
        id: i.id,
        name: i.name,
        imageUrl: i.imageUrl,
        price: i.price,
        quantity: i.quantity,
      })),
      totalPrice
    );
    if (remember) saveShipping(form);
    // 주문 저장은 아직 브라우저(orderStorage)라 서버 장바구니만 비워요. 주문 API 전환은 SCRUM-30
    clearCart().catch(() => {});
    router.push("/order/complete");
  };

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="grid gap-8 lg:grid-cols-[1fr_320px]"
    >
      {/* 배송 정보 */}
      <section className="rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-gray-900">배송 정보</h2>
          {saved && (
            <button
              type="button"
              onClick={loadSaved}
              className="rounded-lg border border-brand-line px-3 py-1.5 text-sm font-medium text-brand transition hover:bg-gray-50"
            >
              저장된 배송 정보 불러오기
            </button>
          )}
        </div>

        <div className="mt-5 space-y-4">
          <label className="block text-sm font-medium text-gray-700">
            받는 분
            <input
              className={inputClass}
              value={form.buyerName}
              onChange={handleChange("buyerName")}
              placeholder="이름"
            />
            {errors.buyerName && (
              <span className="mt-1 block text-xs text-red-500">{errors.buyerName}</span>
            )}
          </label>

          <label className="block text-sm font-medium text-gray-700">
            휴대폰 번호
            <input
              className={inputClass}
              value={form.phone}
              onChange={handleChange("phone")}
              placeholder="010-1234-5678"
              inputMode="tel"
            />
            {errors.phone && (
              <span className="mt-1 block text-xs text-red-500">{errors.phone}</span>
            )}
          </label>

          <label className="block text-sm font-medium text-gray-700">
            우편번호
            <input
              className={inputClass}
              value={form.zipcode}
              onChange={handleChange("zipcode")}
              placeholder="12345"
              inputMode="numeric"
              maxLength={5}
            />
            {errors.zipcode && (
              <span className="mt-1 block text-xs text-red-500">{errors.zipcode}</span>
            )}
          </label>

          <label className="block text-sm font-medium text-gray-700">
            주소
            <input
              className={inputClass}
              value={form.address1}
              onChange={handleChange("address1")}
              placeholder="도로명 주소"
            />
            {errors.address1 && (
              <span className="mt-1 block text-xs text-red-500">{errors.address1}</span>
            )}
          </label>

          <label className="block text-sm font-medium text-gray-700">
            상세 주소 (선택)
            <input
              className={inputClass}
              value={form.address2}
              onChange={handleChange("address2")}
              placeholder="동/호수 등"
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4"
            />
            이 배송 정보를 다음 주문에도 사용하기
          </label>
        </div>
      </section>

      {/* 주문 요약 */}
      <aside className="h-fit rounded-xl border border-gray-200 p-5">
        <h2 className="font-bold text-gray-900">주문 상품</h2>
        <ul className="mt-3 space-y-2 text-sm text-gray-600">
          {items.map((i) => (
            <li key={i.id} className="flex justify-between gap-3">
              <span className="line-clamp-1">
                {i.name} × {i.quantity}
              </span>
              <span className="shrink-0">
                {(i.price * i.quantity).toLocaleString()}원
              </span>
            </li>
          ))}
        </ul>

        <div className="mt-4 flex justify-between text-sm text-gray-600">
          <span>상품 수량</span>
          <span>{totalCount}개</span>
        </div>
        <div className="mt-2 flex justify-between border-t border-gray-200 pt-4">
          <span className="font-semibold text-gray-900">총 결제금액</span>
          <span className="text-xl font-bold text-gray-900">
            {totalPrice.toLocaleString()}원
          </span>
        </div>

        <button
          type="submit"
          className="mt-5 w-full rounded-lg bg-brand py-3 font-semibold text-white transition hover:bg-brand-dark"
        >
          주문 완료하기
        </button>
      </aside>
    </form>
  );
}