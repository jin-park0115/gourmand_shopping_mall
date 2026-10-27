"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { ApiError, loginHref } from "@/lib/api";
import { fetchOrder, type Order } from "@/lib/orders";
import { ListSkeleton } from "@/components/Skeletons";

type Loaded = { orderId: number; order: Order | null; error: string | null };

export default function OrderComplete() {
    const orderId = Number(useSearchParams().get("orderId")) || null;
    const { member, ready } = useAuth();
    const [loaded, setLoaded] = useState<Loaded | null>(null);

    // 주문 번호로 서버에서 내 주문을 불러와요 (남의 주문 · 없는 주문은 404)
    useEffect(() => {
        if (!orderId || !member) return;
        let cancelled = false;
        fetchOrder(orderId)
            .then((order) => ({ orderId, order, error: null }))
            .catch((e) => ({
                orderId,
                order: null,
                // 없는 주문(404) · 남의 주문(403)은 같은 안내로
                error: e instanceof ApiError && (e.status === 404 || e.status === 403) ? null : "주문 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.",
            }))
            .then((res) => !cancelled && setLoaded(res));
        return () => {
            cancelled = true;
        };
    }, [orderId, member]);

    if (!ready || (orderId && member && loaded?.orderId !== orderId)) {
        return <ListSkeleton rows={2} thumb label="주문 정보를 불러오는 중이에요" className="py-10" />;
    }

    if (orderId && !member) {
        return (
            <Notice
                text="로그인하면 주문 내역을 확인할 수 있어요."
                href={loginHref(`/order/complete?orderId=${orderId}`)}
                label="로그인하기"
            />
        );
    }

    if (loaded?.error) return <Notice text={loaded.error} href="/mypage" label="주문 내역 보기" />;

    const order = loaded?.order;
    if (!order) return <Notice text="확인할 주문 내역이 없어요." href="/" label="홈으로" />;

    return (
        <div className="mx-auto max-w-2xl">
            <div className="text-center">
                <h1 className="text-2xl font-bold text-gray-900">주문이 완료되었어요</h1>
                <p className="mt-2 text-sm text-gray-500">
                    주문번호 <span className="font-semibold text-gray-900">{order.orderId}</span>
                    {" · "}
                    {order.status}
                    {order.payment && ` · ${order.payment.status}`}
                </p>
            </div>

            <section className="mt-8 rounded-xl border border-gray-200 p-6">
                <h2 className="font-bold text-gray-900">주문 상품</h2>
                <ul className="mt-4 divide-y divide-gray-100">
                    {order.items.map((i) => (
                        <li key={i.productId} className="flex items-center gap-4 py-3">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                                src={i.imageUrl}
                                alt={i.name}
                                className="h-16 w-16 rounded-lg object-cover"
                            />
                            <div className="min-w-0 flex-1">
                                <p className="line-clamp-1 text-sm font-medium text-gray-900">{i.name}</p>
                                <p className="text-xs text-gray-500">
                                    {i.unitPrice.toLocaleString()}원 × {i.quantity}
                                </p>
                            </div>
                            <p className="text-sm font-semibold text-gray-900">
                                {i.subtotal.toLocaleString()}원
                            </p>
                        </li>
                    ))}
                </ul>
                <div className="mt-2 flex justify-between border-t border-gray-200 pt-4">
                    <span className="font-semibold text-gray-900">총 결제금액</span>
                    <span className="text-xl font-bold text-gray-900">
                        {order.totalPrice.toLocaleString()}원
                    </span>
                </div>
            </section>

            <section className="mt-4 rounded-xl border border-gray-200 p-6 text-sm text-gray-700">
                <h2 className="font-bold text-gray-900">배송 정보</h2>
                <dl className="mt-4 space-y-2">
                    <div className="flex gap-4">
                        <dt className="w-20 text-gray-500">받는 분</dt>
                        <dd>{order.recipient}</dd>
                    </div>
                    <div className="flex gap-4">
                        <dt className="w-20 text-gray-500">연락처</dt>
                        <dd>{order.phone}</dd>
                    </div>
                    <div className="flex gap-4">
                        <dt className="w-20 text-gray-500">주소</dt>
                        <dd>
                            ({order.zipcode}) {order.address1} {order.address2}
                        </dd>
                    </div>
                </dl>
            </section>

            <div className="mt-8 flex justify-center gap-3">
                <Link
                    href="/mypage"
                    className="inline-block rounded-lg border border-brand-line px-6 py-3 font-semibold text-brand transition hover:bg-gray-50"
                >
                    주문 내역 보기
                </Link>
                <Link
                    href="/"
                    className="inline-block rounded-lg bg-brand px-6 py-3 font-semibold text-white transition hover:bg-brand-dark"
                >
                    쇼핑 계속하기
                </Link>
            </div>
        </div>
    );
}

function Notice({ text, href, label }: { text: string; href: string; label: string }) {
    return (
        <div className="py-20 text-center">
            <p className="text-gray-600">{text}</p>
            <Link
                href={href}
                className="mt-4 inline-block rounded-lg bg-brand px-5 py-2.5 font-semibold text-white transition hover:bg-brand-dark"
            >
                {label}
            </Link>
        </div>
    );
}
