"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { cartErrorMessage, useCart } from "@/components/CartProvider";
import { type OrderInput } from "@/lib/orderStorage";
import { fetchSavedAddress, placeOrder, shippingErrorField } from "@/lib/orders";
import { ListSkeleton } from "@/components/Skeletons";

type Errors = Partial<Record<keyof OrderInput, string>>;

// 빈칸으로 시작해요. 지난 주문 때 저장한 배송 정보는 "저장된 배송 정보 불러오기"로 채워요
const EMPTY: OrderInput = {
  buyerName: "",
  phone: "",
  zipcode: "",
  address1: "",
  address2: "",
};

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
  const { member } = useAuth();
  const { items, hydrated, totalCount, totalPrice, orderable, reload } = useCart();
  const [form, setForm] = useState<OrderInput>(EMPTY);
  const [errors, setErrors] = useState<Errors>({});
  const [submitted, setSubmitted] = useState(false);
  const [remember, setRemember] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // 저장된 배송 정보는 내 계정(서버)에 있어요. 누구의 것인지 같이 저장해서 회원이 바뀌면 쓰지 않아요
  const memberId = member?.id ?? null;
  const [savedFor, setSavedFor] = useState<{ memberId: number; value: OrderInput | null } | null>(null);
  useEffect(() => {
    if (memberId === null) return;
    let cancelled = false;
    fetchSavedAddress().then(
      (value) => !cancelled && setSavedFor({ memberId, value }),
      () => !cancelled && setSavedFor({ memberId, value: null }) // 못 불러오면 버튼만 숨겨요
    );
    return () => {
      cancelled = true;
    };
  }, [memberId]);
  const saved = savedFor?.memberId === memberId ? savedFor.value : null;

  // 주문서에 들어올 때마다 장바구니를 새로 받아요. 처음 불러온 뒤 가격이 바뀌었거나 다른 탭에서 담았으면
  // 그대로 보여 주면 화면과 다른 금액으로 결제돼서요 (그래도 어긋나면 서버가 expectedTotalPrice 로 막아요)
  useEffect(() => {
    reload();
  }, [reload]);

  // 주문을 마치고 다른 화면으로 가도 이 화면의 상태가 보존돼요 (Next cacheComponents).
  // 그대로 두면 뒤로 가기로 돌아왔을 때 '주문하는 중…' · 0원으로 멈춰서, 화면을 떠날 때 처음 상태로 되돌려요
  useEffect(
    () => () => {
      setSubmitting(false);
      setSubmitted(false);
    },
    []
  );

  if (!hydrated) {
    return <ListSkeleton rows={3} label="주문서를 불러오는 중이에요" className="py-6" />;
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const found = validate(form);
    setErrors(found);
    setSubmitError(null);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      // 서버가 장바구니로 주문을 만들고 장바구니를 비워요 (재고 차감 · 결제완료까지 한 번에, SCRUM-29)
      const order = await placeOrder(form, remember, totalPrice);
      setSubmitted(true); // 비워진 장바구니로 "비어 있어요" 화면이 깜빡이지 않게
      reload(); // 헤더 장바구니 숫자도 0 으로
      // replace: 주문 완료에서 뒤로 가기를 누르면 끝난 주문서가 아니라 그 전 화면(장바구니)으로
      router.replace(`/order/complete?orderId=${order.orderId}`);
    } catch (err) {
      // 배송 정보 문제면 해당 칸 아래에, 그 밖의 이유(재고 부족 등)는 버튼 위에 서버 문구 그대로
      const field = shippingErrorField(err);
      if (field) setErrors({ [field]: cartErrorMessage(err) });
      else setSubmitError(cartErrorMessage(err));
      reload(); // 재고가 바뀌었을 수 있어서 장바구니를 다시 받아요 (품절 · 재고 초과면 주문서 대신 장바구니 안내로)
      setSubmitting(false);
    }
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
            이 배송 정보를 내 계정에 저장하고 다음 주문에도 사용하기
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

        {submitError && (
          <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {submitError}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="mt-5 w-full rounded-lg bg-brand py-3 font-semibold text-white transition hover:bg-brand-dark disabled:bg-gray-300"
        >
          {submitting ? "주문하는 중…" : "주문 완료하기"}
        </button>
      </aside>
    </form>
  );
}