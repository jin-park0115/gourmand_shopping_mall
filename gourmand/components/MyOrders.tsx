"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/Toast";
import { ApiError, loginHref, type Page } from "@/lib/api";
import { ORDER_STATUSES, type OrderInput } from "@/lib/orderStorage";
import { CANCELLABLE_STATUSES, cancelOrder, fetchMyOrders, fetchSavedAddress, type Order } from "@/lib/orders";
import { ListSkeleton } from "@/components/Skeletons";

const PAGE_SIZE = 5;

// 기간: 오늘부터 N개월 전 (주문일은 서버에 KST 로 저장돼요)
const PERIODS = [
  { label: "전체 기간", months: 0 },
  { label: "최근 1개월", months: 1 },
  { label: "최근 3개월", months: 3 },
  { label: "최근 6개월", months: 6 },
] as const;

function monthsAgo(months: number) {
  if (!months) return undefined;
  const d = new Date();
  d.setMonth(d.getMonth() - months);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// 서버 시간 "2026-10-26T14:03:00" (KST, 시간대 없음) → "2026.10.26 14:03"
function formatDate(value: string) {
  return value.slice(0, 16).replace("T", " ").replaceAll("-", ".");
}

type Loaded = { key: string; page: Page<Order> | null; error: string | null };

export default function MyOrders() {
  const { member, ready } = useAuth();
  const [status, setStatus] = useState("");
  const [months, setMonths] = useState(0);
  const [page, setPage] = useState(1);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [cancelling, setCancelling] = useState<number | null>(null);
  const toast = useToast(); // 취소 결과는 토스트로 (목록이 길어도 보이게)

  // 저장된 배송 정보는 내 계정(서버)에 있어요. 누구의 것인지 같이 저장해서 회원이 바뀌면 쓰지 않아요
  const memberId = member?.id ?? null;
  const [savedFor, setSavedFor] = useState<{ memberId: number; value: OrderInput | null } | null>(null);
  useEffect(() => {
    if (memberId === null) return;
    let cancelled = false;
    fetchSavedAddress().then(
      (value) => !cancelled && setSavedFor({ memberId, value }),
      () => !cancelled && setSavedFor({ memberId, value: null })
    );
    return () => {
      cancelled = true;
    };
  }, [memberId]);
  const shipping = savedFor?.memberId === memberId ? savedFor.value : null;

  const from = monthsAgo(months);
  const key = JSON.stringify({ status, from, page, reloadKey });

  // 조건이 바뀔 때마다 서버에서 내 주문을 불러와요
  useEffect(() => {
    if (!member) return;
    let cancelled = false;
    fetchMyOrders({ status: status || undefined, from, page, size: PAGE_SIZE })
      .then((res) => ({ key, page: res, error: null }))
      .catch((e) => ({
        key,
        page: null,
        error: e instanceof ApiError ? e.message : "주문 내역을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.",
      }))
      .then((res) => !cancelled && setLoaded(res));
    return () => {
      cancelled = true;
    };
    // key 에 status · from · page · reloadKey 가 다 들어 있어요
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [member, key]);

  // 필터를 바꾸면 1쪽부터
  const changeStatus = (value: string) => {
    setStatus(value);
    setPage(1);
  };
  const changeMonths = (value: number) => {
    setMonths(value);
    setPage(1);
  };

  async function handleCancel(order: Order) {
    if (!confirm(`주문번호 ${order.orderId}을(를) 취소할까요? 결제가 취소되고 되돌릴 수 없어요.`)) return;
    setCancelling(order.orderId);
    try {
      await cancelOrder(order.orderId);
      toast(`주문번호 ${order.orderId}을(를) 취소했어요.`);
    } catch (e) {
      // 예: 그사이 관리자가 출고해서 '배송중' 이면 서버가 취소할 수 없다고 알려 줘요
      toast(e instanceof ApiError ? e.message : "주문을 취소하지 못했어요.", "error");
    } finally {
      setCancelling(null);
      setReloadKey((k) => k + 1); // 바뀐 상태를 다시 받아요 (상태 필터에서 빠질 수도 있어서 목록째)
    }
  }

  if (!ready) {
    return <ListSkeleton rows={3} thumb label="주문 내역을 불러오는 중이에요" className="py-6" />;
  }

  if (!member) {
    return (
      <div className="rounded-xl border border-gray-200 py-16 text-center">
        <p className="text-gray-600">로그인하면 주문 내역을 볼 수 있어요.</p>
        <Link
          href={loginHref("/mypage")}
          className="mt-4 inline-block rounded-lg bg-brand px-5 py-2.5 font-semibold text-white transition hover:bg-brand-dark"
        >
          로그인하기
        </Link>
      </div>
    );
  }

  const current = loaded?.key === key ? loaded : null;
  const result = current?.page;

  return (
    <div className="space-y-8">
      {/* 저장된 배송 정보 */}
      <section className="rounded-xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900">저장된 배송 정보</h2>
        {shipping ? (
          <dl className="mt-4 space-y-2 text-sm text-gray-700">
            <div className="flex gap-4">
              <dt className="w-20 text-gray-500">받는 분</dt>
              <dd>{shipping.buyerName}</dd>
            </div>
            <div className="flex gap-4">
              <dt className="w-20 text-gray-500">연락처</dt>
              <dd>{shipping.phone}</dd>
            </div>
            <div className="flex gap-4">
              <dt className="w-20 text-gray-500">주소</dt>
              <dd>
                ({shipping.zipcode}) {shipping.address1} {shipping.address2}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="mt-3 text-sm text-gray-500">
            아직 저장된 배송 정보가 없어요. 주문할 때 &lsquo;내 계정에 저장&rsquo;을 고르면 여기에 보여요.
          </p>
        )}
      </section>

      {/* 주문 내역 */}
      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-bold text-gray-900">
            주문 내역 <span className="text-gray-400">({result?.total ?? 0})</span>
          </h2>
          <div className="flex gap-2 text-sm">
            <select
              aria-label="주문 상태"
              value={status}
              onChange={(e) => changeStatus(e.target.value)}
              className="rounded-lg border border-gray-300 px-2 py-1.5"
            >
              <option value="">전체 상태</option>
              {ORDER_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select
              aria-label="주문 기간"
              value={months}
              onChange={(e) => changeMonths(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-2 py-1.5"
            >
              {PERIODS.map((p) => (
                <option key={p.months} value={p.months}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {!current ? (
          <ListSkeleton rows={3} thumb label="주문 내역을 불러오는 중이에요" />
        ) : current.error ? (
          <div className="rounded-xl border border-gray-200 py-16 text-center">
            <p className="text-gray-600">{current.error}</p>
            <button
              type="button"
              onClick={() => setReloadKey((k) => k + 1)}
              className="mt-4 inline-block rounded-lg bg-brand px-5 py-2.5 font-semibold text-white transition hover:bg-brand-dark"
            >
              다시 불러오기
            </button>
          </div>
        ) : !result || result.items.length === 0 ? (
          <div className="rounded-xl border border-gray-200 py-16 text-center">
            <p className="text-gray-600">
              {status || months ? "조건에 맞는 주문이 없어요." : "아직 주문 내역이 없어요."}
            </p>
            <Link
              href="/"
              className="mt-4 inline-block rounded-lg bg-brand px-5 py-2.5 font-semibold text-white transition hover:bg-brand-dark"
            >
              쇼핑하러 가기
            </Link>
          </div>
        ) : (
          <>
            <ul className="space-y-4">
              {result.items.map((order) => (
                <li key={order.orderId} className="rounded-xl border border-gray-200 p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-semibold text-gray-900">주문번호 {order.orderId}</p>
                      <p className="text-xs text-gray-500">{formatDate(order.orderedAt)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                        {order.status}
                      </span>
                      {CANCELLABLE_STATUSES.includes(order.status) && (
                        <button
                          type="button"
                          onClick={() => handleCancel(order)}
                          disabled={cancelling !== null}
                          className="rounded-full border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 transition hover:border-red-400 hover:text-red-500 disabled:opacity-50"
                        >
                          {cancelling === order.orderId ? "취소하는 중…" : "주문 취소"}
                        </button>
                      )}
                    </div>
                  </div>

                  <ul className="mt-4 divide-y divide-gray-100">
                    {order.items.map((i) => (
                      <li key={i.productId} className="flex items-center gap-3 py-2.5">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={i.imageUrl} alt={i.name} className="h-12 w-12 rounded-lg object-cover" />
                        <div className="min-w-0 flex-1">
                          <Link
                            href={`/products/${i.productId}`}
                            className="line-clamp-1 text-sm font-medium text-gray-900 hover:underline"
                          >
                            {i.name}
                          </Link>
                          <p className="text-xs text-gray-500">
                            {i.unitPrice.toLocaleString()}원 × {i.quantity}
                          </p>
                        </div>
                        <p className="text-sm font-semibold text-gray-900">{i.subtotal.toLocaleString()}원</p>
                      </li>
                    ))}
                  </ul>

                  <div className="mt-2 flex justify-between border-t border-gray-200 pt-3 text-sm">
                    <span className="text-gray-600">
                      총 결제금액{order.payment && <span className="ml-1 text-xs text-gray-400">({order.payment.status})</span>}
                    </span>
                    <span className="font-bold text-gray-900">{order.totalPrice.toLocaleString()}원</span>
                  </div>

                  {order.courier && order.trackingNo && (
                    <p className="mt-3 rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700">
                      <span className="text-gray-500">택배사</span> {order.courier}
                      <span className="ml-3 text-gray-500">운송장 번호</span>{" "}
                      <span className="font-semibold tabular-nums">{order.trackingNo}</span>
                    </p>
                  )}

                  <p className="mt-3 text-xs text-gray-500">
                    배송지: {order.recipient} · {order.phone} · ({order.zipcode}) {order.address1} {order.address2}
                  </p>
                </li>
              ))}
            </ul>

            {result.pages > 1 && (
              <nav aria-label="주문 내역 페이지" className="mt-6 flex items-center justify-center gap-3 text-sm">
                <button
                  type="button"
                  onClick={() => setPage((p) => p - 1)}
                  disabled={page <= 1}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 disabled:text-gray-300"
                >
                  이전
                </button>
                <span className="text-gray-600">
                  {page} / {result.pages}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= result.pages}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 disabled:text-gray-300"
                >
                  다음
                </button>
              </nav>
            )}
          </>
        )}
      </section>
    </div>
  );
}
