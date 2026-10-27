"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

import { useAuth } from "@/components/AuthProvider";
import { ApiError, getToken, loginHref, type Page } from "@/lib/api";
import type { Member } from "@/lib/auth";
import {
  changeOrderStatus,
  COURIERS,
  fetchAdminOrder,
  fetchAdminOrders,
  fetchOrderSummary,
  type AdminOrder,
  type OrderStatus,
  type OrderSummary,
  type StatusChange,
} from "@/lib/adminOrders";
import { ORDER_STATUSES } from "@/lib/orderStorage";
import { ListSkeleton } from "@/components/Skeletons";

const PAGE_SIZE = 20;

// ── 배송 상태 표시 (색 + 글자로 구분) ──
const STATUS_STYLE: Record<OrderStatus, { badge: string; dot: string }> = {
  접수: { badge: "bg-[#EEF0F3] text-[#384250]", dot: "bg-[#384250]" },
  상품준비중: { badge: "bg-[#FFF0D4] text-[#7A4A00]", dot: "bg-[#7A4A00]" },
  배송중: { badge: "bg-[#E2EDFA] text-[#1D4B85]", dot: "bg-[#1D4B85]" },
  배송완료: { badge: "bg-[#E1F2E6] text-[#1D6436]", dot: "bg-[#1D6436]" },
  배송지연: { badge: "bg-[#FCE3EB] text-[#9B1239]", dot: "bg-[#9B1239]" },
  주문취소: { badge: "bg-[#F0EEEC] text-[#5F5550]", dot: "bg-[#5F5550]" },
};
const styleOf = (s: string) => STATUS_STYLE[s as OrderStatus] ?? STATUS_STYLE["접수"];

const STEPS = ["접수", "상품준비중", "배송중", "배송완료"];
const STEP_INDEX: Record<string, number> = { 접수: 0, 상품준비중: 1, 배송중: 2, 배송지연: 2, 배송완료: 3 };

const won = (n: number) => `${n.toLocaleString("ko-KR")}원`;
const pad = (n: number) => String(n).padStart(2, "0");
const fmt = (iso: string) => {
  const d = new Date(iso);
  return `${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
const unitsOf = (o: AdminOrder) => o.items.reduce((s, i) => s + i.quantity, 0);
// 이력 첫 줄 '접수'는 주문 생성(SCRUM-29) 때 생겨요. 그 전에 만든 주문은 주문 시각을 '접수'로 봐요
const historyOf = (o: AdminOrder) =>
  o.history?.some((h) => h.status === "접수") ? o.history : [{ status: "접수", at: o.orderedAt, note: null }, ...(o.history ?? [])];
// 서버가 보낸 오류 메시지는 그대로, 서버에 닿지 못했으면 안내 문구를 보여 줘요
const errorText = (e: unknown) =>
  e instanceof ApiError ? e.message : "서버에 연결하지 못했어요. 백엔드가 켜져 있는지 확인해 주세요.";

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-bold ${styleOf(status).badge}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status}
    </span>
  );
}

function Icon({ d }: { d: string }) {
  return (
    <svg aria-hidden="true" className="h-[18px] w-[18px] flex-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

function Notice({ children, error = false }: { children: React.ReactNode; error?: boolean }) {
  return <p role={error ? "alert" : undefined} className={`px-5 py-32 text-center ${error ? "font-medium text-[#9B1239]" : "text-[#6E5B50]"}`}>{children}</p>;
}

// 관리자만 들어와요: 로그인 안 했으면 로그인 화면으로, 고객 계정이면 안내만 보여 줘요.
// 화면은 길만 막고, 진짜 검사는 백엔드 require_admin 이 해요 (토큰 없음 · 로그아웃 401, 고객 403)
export default function AdminDashboard() {
  const { member, ready, logout } = useAuth();
  const leaving = useRef(false); // 로그아웃 버튼으로 나가는 중 (이때는 '로그인 필요' 이동을 하지 않아요)

  // 토큰이 남아 있으면 아직 확인 중이라 기다려요 (로그인 직후 들어왔을 때 로그인 화면으로 튕기지 않게)
  useEffect(() => {
    if (ready && !member && !getToken() && !leaving.current) location.assign(loginHref("/admin"));
  }, [ready, member]);

  // 로그아웃하면 그냥 로그인 화면으로: 다음에 누가 로그인하든 역할에 맞는 화면으로 가요
  const onLogout = async () => {
    leaving.current = true;
    await logout();
    location.replace("/login");
  };

  if (!ready || !member) return <Notice>로그인 상태를 확인하고 있어요…</Notice>;
  if (member.role !== "admin") return <Forbidden member={member} onLogout={onLogout} />;
  return <Dashboard member={member} onLogout={onLogout} />;
}

function Forbidden({ member, onLogout }: { member: Member; onLogout: () => Promise<void> }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#FBF8F5] px-5 text-center text-[#2A1A12]">
      <h1 className="text-2xl font-extrabold">관리자만 사용할 수 있어요</h1>
      <p className="text-[#6E5B50]">지금 로그인한 {member.email} 은 고객 계정이에요. 관리자 계정으로 다시 로그인해 주세요.</p>
      <div className="flex flex-wrap justify-center gap-2">
        <button type="button" onClick={() => void onLogout()} className="h-11 rounded-xl bg-brand px-5 font-bold text-white transition hover:bg-brand-dark">
          로그아웃하고 다시 로그인
        </button>
        <Link href="/" className="flex h-11 items-center rounded-xl border border-[#E3D5CA] bg-white px-5 font-bold text-[#3E1A08] transition hover:bg-[#FBF8F5]">
          쇼핑몰로 가기
        </Link>
      </div>
    </div>
  );
}

function Dashboard({ member, onLogout }: { member: Member; onLogout: () => Promise<void> }) {
  const [filter, setFilter] = useState<"전체" | OrderStatus>("전체");
  const [query, setQuery] = useState("");
  const [keyword, setKeyword] = useState(""); // 서버로 보내는 검색어 (입력을 잠깐 멈추면 바뀌어요)
  const [page, setPage] = useState(1);
  const [list, setList] = useState<Page<AdminOrder> | null>(null);
  const [summary, setSummary] = useState<OrderSummary | null>(null);
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<AdminOrder | null>(null);
  const [version, setVersion] = useState(0); // 상태를 바꾸면 올려서 목록 · 요약을 다시 불러와요

  // 검색어는 입력을 0.3초 멈추면 서버에 물어봐요 (주문번호 · 받는 사람 · 연락처 · 상품명)
  useEffect(() => {
    const timer = setTimeout(() => {
      setKeyword(query.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // 주문 목록 (GET /admin/orders)
  useEffect(() => {
    let alive = true;
    fetchAdminOrders({ status: filter === "전체" ? undefined : filter, q: keyword, page, size: PAGE_SIZE })
      .then((res) => {
        if (!alive) return;
        setList(res);
        setLoadedAt(new Date());
        setLoadError(null);
        // 처음에는 맨 위 주문을 열어 둬요
        setSelectedId((id) => id ?? res.items[0]?.orderId ?? null);
      })
      .catch((e) => {
        if (alive) setLoadError(errorText(e));
      });
    return () => {
      alive = false;
    };
  }, [filter, keyword, page, version]);

  // 위쪽 카드 · 상태 탭 개수 · TOP 5 (GET /admin/orders/summary)
  useEffect(() => {
    let alive = true;
    fetchOrderSummary(keyword)
      .then((res) => {
        if (alive) setSummary(res);
      })
      .catch((e) => {
        if (alive) setLoadError(errorText(e));
      });
    return () => {
      alive = false;
    };
  }, [keyword, version]);

  // 고른 주문의 상세 + 상태 이력 (GET /admin/orders/{orderId})
  useEffect(() => {
    if (selectedId === null) return;
    let alive = true;
    fetchAdminOrder(selectedId)
      .then((res) => {
        if (alive) setDetail(res);
      })
      .catch((e) => {
        if (alive) setLoadError(errorText(e));
      });
    return () => {
      alive = false;
    };
  }, [selectedId]);

  // 상태 바꾸기 (PATCH /admin/orders/{orderId}/status). 실패하면 OrderDetail 이 서버 메시지를 보여 줘요
  async function change(body: StatusChange) {
    if (!detail) return;
    const orderId = detail.orderId;
    try {
      setDetail(await changeOrderStatus(orderId, body));
    } catch (e) {
      // 409 = 다른 관리자가 먼저 바꿨어요. 화면이 옛 상태로 남지 않게 지금 상태를 다시 불러와요
      if (e instanceof ApiError && e.status === 409) await fetchAdminOrder(orderId).then(setDetail, () => undefined);
      throw e;
    } finally {
      setVersion((v) => v + 1);
    }
  }

  if (!list || !summary || !loadedAt) {
    return loadError ? <Notice error>{loadError}</Notice> : <ListSkeleton rows={6} thumb label="주문을 불러오는 중이에요" className="px-5 py-10" />;
  }

  const counts = summary.statusCounts;
  const kpis = [
    { label: "오늘 주문", value: `${summary.todayOrders}건`, sub: `상품 ${summary.todayUnits}개 · 취소 제외`, warn: false },
    { label: "오늘 매출", value: won(summary.todaySales), sub: "취소한 주문은 빼고 계산해요", warn: false },
    { label: "출고 대기", value: `${summary.waitingShipment}건`, sub: `접수 ${counts["접수"] ?? 0} · 상품준비중 ${counts["상품준비중"] ?? 0}`, warn: false },
    { label: "배송 지연", value: `${counts["배송지연"] ?? 0}건`, sub: "고객 안내가 필요해요", warn: true },
  ];
  const tabCount = (key: "전체" | OrderStatus) => (key === "전체" ? summary.total : counts[key] ?? 0);
  const maxUnits = summary.topProducts[0]?.units ?? 1;
  const pager = "h-9 rounded-lg border border-[#E3D5CA] bg-white px-3 font-bold text-[#3E1A08] transition hover:bg-[#FBF8F5] disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div className="flex min-h-screen flex-wrap bg-[#FBF8F5] text-[14px] leading-normal text-[#2A1A12]">
      {/* ── 사이드바 ── */}
      <aside className="flex flex-[1_1_232px] flex-col gap-4 bg-[#3E1A08] px-4 py-4 text-[#F3E6DA] lg:gap-7 lg:py-6">
        <div className="flex items-center justify-center rounded-2xl bg-[#FBF3EA] px-3 py-2 lg:py-2.5">
          <img src="/images/common/logo.png" alt="구르망 GOURMAND" className="h-10 w-auto lg:h-[52px]" />
        </div>
        <p className="-mb-4 hidden px-3 text-[11px] font-bold tracking-[0.12em] text-[#C9A58C] lg:block">ADMIN</p>
        <nav aria-label="관리자 메뉴" className="flex flex-col gap-1">
          <span aria-current="page" className="flex items-center gap-3 rounded-[10px] bg-[#FBF3EA] px-3 py-[11px] font-bold text-[#3E1A08]">
            <Icon d="M3 7h11v10H3zM14 10h4l3 3v4h-7M5.2 18a1.8 1.8 0 1 0 3.6 0a1.8 1.8 0 1 0-3.6 0M15.7 18a1.8 1.8 0 1 0 3.6 0a1.8 1.8 0 1 0-3.6 0" />
            주문·배송 관리
            <span className="ml-auto rounded-full bg-accent px-2 text-[11px] font-bold tabular-nums text-white">{summary.waitingShipment}</span>
          </span>
          {[
            { label: "대시보드", d: "M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z" },
            { label: "상품 관리", d: "M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8M12 13v8" },
            { label: "회원 관리", d: "M5.5 8a3.5 3.5 0 1 0 7 0a3.5 3.5 0 1 0-7 0M2.5 20c.8-3.6 3.4-5.5 6.5-5.5s5.7 1.9 6.5 5.5M16 4.5a3.5 3.5 0 0 1 0 7M18 14.8c1.8.7 3 2.4 3.5 5.2" },
            { label: "리뷰 관리", d: "M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.5 9.7l5.9-.9z" },
          ].map((m) => (
            <span key={m.label} aria-disabled="true" className="hidden items-center gap-3 lg:flex rounded-[10px] px-3 py-[11px] font-medium text-[#E7D3C2]">
              <Icon d={m.d} />
              {m.label}
              <span className="ml-auto text-[11px] text-[#C9A58C]">준비 중</span>
            </span>
          ))}
        </nav>
        <div className="mt-auto flex flex-col gap-3">
          <Link href="/" className="hidden items-center gap-2 px-3 text-[13px] text-[#E7D3C2] hover:text-white lg:flex">
            <Icon d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
            쇼핑몰 화면 보기
          </Link>
          <div className="flex items-center gap-2.5 border-t border-[#F3E6DA]/20 px-3 pt-3.5">
            <span aria-hidden="true" className="flex h-[34px] w-[34px] flex-none items-center justify-center rounded-full bg-accent text-[13px] font-bold text-white">
              {member.name.slice(0, 1)}
            </span>
            <div className="flex min-w-0 flex-col leading-tight">
              <span className="truncate text-[13px] font-bold">{member.name}</span>
              <span className="truncate text-xs text-[#C9A58C]">{member.email}</span>
            </div>
            <button type="button" onClick={() => void onLogout()} className="ml-auto flex-none whitespace-nowrap rounded-lg px-2 py-1 text-xs font-bold text-[#E7D3C2] hover:bg-[#F3E6DA]/10 hover:text-white">
              로그아웃
            </button>
          </div>
        </div>
      </aside>

      {/* ── 본문 ── */}
      <main className="flex min-w-0 flex-[999_1_560px] flex-col gap-6 px-5 pb-14 pt-8 md:px-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <h1 className="text-[28px] font-extrabold tracking-tight">주문·배송 관리</h1>
            <p className="text-[#6E5B50]">
              {loadedAt.getFullYear()}년 {loadedAt.getMonth() + 1}월 {loadedAt.getDate()}일 {pad(loadedAt.getHours())}:{pad(loadedAt.getMinutes())} 기준 · 주문 {summary.total}건
            </p>
          </div>
          <label className="flex h-11 w-[300px] max-w-full items-center gap-2 rounded-xl border border-[#E3D5CA] bg-white px-3.5 text-[#6E5B50] focus-within:border-brand">
            <svg aria-hidden="true" className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
              <circle cx="10.5" cy="10.5" r="6.5" />
              <path d="M16 16l4.5 4.5" />
            </svg>
            <span className="sr-only">주문 검색</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              maxLength={50}
              placeholder="주문번호, 받는 사람, 연락처, 상품명"
              className="min-w-0 flex-1 bg-transparent text-[#2A1A12] outline-none placeholder:text-[#8A7769]"
            />
          </label>
        </div>

        {loadError && (
          <p role="alert" className="rounded-xl bg-[#FCE3EB] px-4 py-3 text-[13px] font-medium text-[#9B1239]">
            {loadError}
          </p>
        )}

        {/* 오늘 요약 */}
        <section aria-label="오늘 요약" className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3 md:gap-4">
          {kpis.map((k) => (
            <div key={k.label} className="flex flex-col gap-1.5 rounded-2xl border border-[#EADFD6] bg-white px-5 py-[18px]">
              <span className="text-[13px] font-medium text-[#6E5B50]">{k.label}</span>
              <span className={`text-[28px] font-extrabold tabular-nums tracking-tight ${k.warn ? "text-[#9B1239]" : ""}`}>{k.value}</span>
              <span className="text-xs text-[#6E5B50]">{k.sub}</span>
            </div>
          ))}
        </section>

        {/* 배송 상태 탭 */}
        <div role="group" aria-label="배송 상태로 거르기" className="flex flex-wrap gap-2">
          {(["전체", ...ORDER_STATUSES] as const).map((key) => {
            const active = filter === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setFilter(key);
                  setPage(1);
                }}
                aria-pressed={active}
                className={`inline-flex h-11 items-center gap-2 rounded-full border px-4 transition ${
                  active ? "border-[#3E1A08] bg-[#3E1A08] font-bold text-white" : "border-[#E3D5CA] bg-white font-medium text-[#3E1A08] hover:border-[#C9A58C]"
                }`}
              >
                <span className={`h-2 w-2 rounded-full ${key === "전체" ? "bg-brand" : styleOf(key).dot} ${active ? "ring-2 ring-white/60" : ""}`} />
                {key}
                <span className="font-bold tabular-nums">{tabCount(key)}</span>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-start gap-6">
          <div className="flex min-w-0 flex-[999_1_600px] flex-col gap-6">
            {/* 주문 목록 */}
            <section aria-label="주문 목록" className="overflow-hidden rounded-2xl border border-[#EADFD6] bg-white">
              <div className="flex items-center justify-between gap-3 border-b border-[#EADFD6] px-5 py-4">
                <h2 className="text-base font-bold">
                  주문 목록 <span className="font-medium tabular-nums text-[#6E5B50]">{list.total}건</span>
                </h2>
                <span className="text-xs text-[#6E5B50]">주문번호를 누르면 상세가 열려요</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] table-fixed text-left">
                  <thead className="bg-[#FBF8F5] text-xs font-bold text-[#6E5B50]">
                    <tr>
                      <th scope="col" className="w-[150px] px-5 py-2.5">주문번호 · 일시</th>
                      <th scope="col" className="w-[110px] py-2.5">받는 사람</th>
                      <th scope="col" className="py-2.5">주문 상품</th>
                      <th scope="col" className="w-[110px] py-2.5 text-right">결제금액</th>
                      <th scope="col" className="w-[132px] px-5 py-2.5">배송 상태</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.items.map((o) => {
                      const first = o.items[0];
                      const isSel = o.orderId === selectedId;
                      return (
                        <tr key={o.orderId} className={`border-t border-[#F1E8E0] ${isSel ? "bg-brand-soft shadow-[inset_3px_0_0_var(--brand)]" : "hover:bg-[#FCF7F2]"}`}>
                          <td className="px-5 py-3">
                            <button
                              type="button"
                              onClick={() => setSelectedId(o.orderId)}
                              aria-label={`${o.orderId}번 주문 상세 보기`}
                              className="whitespace-nowrap text-left font-bold tabular-nums text-brand underline underline-offset-[3px]"
                            >
                              #{o.orderId}
                            </button>
                            <div className="whitespace-nowrap text-xs tabular-nums text-[#6E5B50]">{fmt(o.orderedAt)}</div>
                          </td>
                          <td className="py-3">
                            <div className="truncate whitespace-nowrap font-medium">{o.buyer.buyerName}</div>
                            <div className="truncate whitespace-nowrap text-xs text-[#6E5B50]">{o.buyer.address1.split(" ").slice(0, 2).join(" ")}</div>
                          </td>
                          <td className="py-3 pr-3">
                            <div className="flex min-w-0 items-center gap-2.5">
                              <img src={first?.imageUrl} alt="" className="h-10 w-10 flex-none rounded-lg border border-[#EADFD6] object-cover" />
                              <div className="min-w-0">
                                <div className="truncate">
                                  {first?.name}
                                  {o.items.length > 1 && ` 외 ${o.items.length - 1}건`}
                                </div>
                                <div className="text-xs tabular-nums text-[#6E5B50]">총 {unitsOf(o)}개</div>
                              </div>
                            </div>
                          </td>
                          <td className="whitespace-nowrap py-3 text-right font-bold tabular-nums">{won(o.totalPrice)}</td>
                          <td className="px-5 py-3"><StatusBadge status={o.status} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {list.total === 0 && (
                  <p className="px-5 py-12 text-center text-[#6E5B50]">
                    {keyword || filter !== "전체"
                      ? "조건에 맞는 주문이 없어요. 검색어나 상태를 바꿔 보세요."
                      : "아직 들어온 주문이 없어요. 고객이 주문하면 여기에 보여요."}
                  </p>
                )}
              </div>
              {list.pages > 1 && (
                <div className="flex items-center justify-center gap-3 border-t border-[#EADFD6] px-5 py-3 text-[13px]">
                  <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)} className={pager}>이전</button>
                  <span className="tabular-nums text-[#6E5B50]">{list.page} / {list.pages}</span>
                  <button type="button" disabled={page >= list.pages} onClick={() => setPage(page + 1)} className={pager}>다음</button>
                </div>
              )}
            </section>

            {/* 많이 주문된 상품 */}
            <section aria-label="많이 주문된 상품" className="flex flex-col gap-3.5 rounded-2xl border border-[#EADFD6] bg-white px-5 py-[18px]">
              <div className="flex items-baseline justify-between gap-3">
                <h2 className="text-base font-bold">많이 주문된 상품 TOP 5</h2>
                <span className="text-xs text-[#6E5B50]">취소 제외 · 수량 기준</span>
              </div>
              {summary.topProducts.length === 0 && <p className="text-[13px] text-[#6E5B50]">아직 집계할 주문이 없어요.</p>}
              {summary.topProducts.map((t, i) => (
                <div key={t.id} className="grid grid-cols-[22px_36px_minmax(0,220px)_minmax(48px,1fr)_48px] items-center gap-3">
                  <span className="font-extrabold tabular-nums text-brand">{i + 1}</span>
                  <img src={t.imageUrl} alt="" className="h-9 w-9 rounded-lg border border-[#EADFD6] object-cover" />
                  <span className="truncate">{t.name}</span>
                  <span className="block h-2.5 overflow-hidden rounded-full bg-[#F3EAE2]">
                    <span className="block h-full rounded-full bg-brand" style={{ width: `${Math.round((t.units / maxUnits) * 100)}%` }} />
                  </span>
                  <span className="text-right font-bold tabular-nums">{t.units}개</span>
                </div>
              ))}
            </section>
          </div>

          {/* 주문 상세 */}
          {selectedId !== null &&
            (detail?.orderId === selectedId ? (
              <OrderDetail key={detail.orderId} order={detail} onChange={change} />
            ) : (
              <aside aria-label="주문 상세" className="min-w-0 flex-[1_1_340px] rounded-2xl border border-[#EADFD6] bg-white p-5">
                <ListSkeleton rows={3} label="주문 상세를 불러오는 중이에요" />
              </aside>
            ))}
        </div>
      </main>
    </div>
  );
}

// ── 주문 상세 패널 ──
// 처리 버튼은 서버가 알려 준 nextStatuses 로만 보여 줘요 (규칙은 백엔드 도메인 SCRUM-32 한 곳에)
function OrderDetail({ order: o, onChange }: { order: AdminOrder; onChange: (body: StatusChange) => Promise<void> }) {
  const [courier, setCourier] = useState(COURIERS[0]);
  const [trackingNo, setTrackingNo] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 서버가 거절하면(409 · 422) 그 메시지를 그대로 보여 줘요
  async function run(body: StatusChange) {
    setBusy(true);
    setError(null);
    try {
      await onChange(body);
      setTrackingNo("");
      setNote("");
    } catch (e) {
      const stale = e instanceof ApiError && e.status === 409;
      setError(stale ? `${errorText(e)} 다른 관리자가 먼저 바꿨을 수 있어서 지금 상태를 다시 불러왔어요.` : errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const history = historyOf(o);
  const timeOf = (status: string) => [...history].reverse().find((h) => h.status === status)?.at;
  const reached = o.status === "주문취소"
    ? Math.max(...history.map((h) => STEP_INDEX[h.status] ?? 0))
    : STEP_INDEX[o.status] ?? 0;
  const delayed = o.status === "배송지연";
  const canceled = o.status === "주문취소";
  const can = (s: OrderStatus) => o.nextStatuses.includes(s);
  const reason = note.trim() || undefined;

  const secondary = "h-11 flex-1 rounded-xl border border-[#E3D5CA] bg-white font-bold text-[#3E1A08] transition hover:bg-[#FBF8F5] disabled:cursor-wait disabled:opacity-60";
  const primary = "h-12 w-full rounded-xl bg-brand text-[15px] font-bold text-white transition hover:bg-brand-dark disabled:cursor-wait disabled:opacity-60";

  return (
    <aside aria-label="주문 상세" className="min-w-0 flex-[1_1_340px] overflow-hidden rounded-2xl border border-[#EADFD6] bg-white">
      <div className="flex flex-col gap-2 border-b border-[#EADFD6] px-5 py-[18px]">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-bold text-[#6E5B50]">주문 상세</span>
          <StatusBadge status={o.status} />
        </div>
        <h2 className="text-xl font-extrabold tabular-nums">#{o.orderId}</h2>
        <span className="text-[13px] tabular-nums text-[#6E5B50]">{fmt(o.orderedAt)} 주문</span>
      </div>

      {o.adminNote && (
        <p className={`mx-5 mt-4 rounded-[10px] px-3 py-2.5 text-[13px] font-medium ${delayed ? "bg-[#FCE3EB] text-[#9B1239]" : "bg-[#F0EEEC] text-[#5F5550]"}`}>
          {o.adminNote}
        </p>
      )}

      {/* 받는 사람 */}
      <dl className="grid grid-cols-[64px_1fr] gap-x-3 gap-y-2 border-b border-[#EADFD6] px-5 py-4 text-[13px]">
        <dt className="text-[#6E5B50]">받는 사람</dt>
        <dd className="font-bold">{o.buyer.buyerName}</dd>
        <dt className="text-[#6E5B50]">연락처</dt>
        <dd className="tabular-nums">{o.buyer.phone}</dd>
        <dt className="text-[#6E5B50]">배송지</dt>
        <dd>({o.buyer.zipcode}) {o.buyer.address1} {o.buyer.address2}</dd>
      </dl>

      {/* 주문 상품 */}
      <div className="flex flex-col gap-3 border-b border-[#EADFD6] px-5 py-4">
        <h3 className="text-sm font-bold">
          주문 상품 <span className="font-medium tabular-nums text-[#6E5B50]">{o.items.length}종 · {unitsOf(o)}개</span>
        </h3>
        {o.items.map((i) => (
          <div key={i.id} className="flex items-center gap-2.5">
            <img src={i.imageUrl} alt="" className="h-11 w-11 flex-none rounded-lg border border-[#EADFD6] object-cover" />
            <div className="min-w-0 flex-1">
              <Link href={`/products/${i.id}`} className="text-[13px] font-medium hover:underline">{i.name}</Link>
              <div className="text-xs tabular-nums text-[#6E5B50]">{won(i.price)} × {i.quantity}개</div>
            </div>
            <span className="text-[13px] font-bold tabular-nums">{won(i.price * i.quantity)}</span>
          </div>
        ))}
        <div className="flex justify-between border-t border-dashed border-[#E3D5CA] pt-2.5 text-[13px]">
          <span className="font-bold">결제 금액</span>
          <span className="text-base font-extrabold tabular-nums text-brand">{won(o.totalPrice)}</span>
        </div>
      </div>

      {/* 배송 진행 */}
      <div className="border-b border-[#EADFD6] px-5 py-4">
        <h3 className="mb-2 text-sm font-bold">배송 진행</h3>
        <ol>
          {STEPS.map((label, i) => {
            const done = i <= reached && !(canceled && !timeOf(label));
            const current = !canceled && i === reached && o.status !== "배송완료";
            const warn = delayed && i === 2;
            const at = warn ? timeOf("배송지연") : timeOf(label);
            return (
              <li key={label} className="grid grid-cols-[20px_1fr] gap-x-3">
                <div className="flex flex-col items-center">
                  <span
                    className={`rounded-full ${current ? "mt-[3px] h-3.5 w-3.5" : "mt-[5px] h-2.5 w-2.5"} ${
                      done ? (warn ? "bg-[#9B1239]" : "bg-brand") : "border-2 border-[#D9CBBF] bg-white"
                    } ${current ? (warn ? "ring-4 ring-[#FCE3EB]" : "ring-4 ring-[#F3E6DA]") : ""}`}
                  />
                  {i < 3 && <span className={`mt-1 w-0.5 flex-1 ${done && i < reached ? "bg-brand" : "bg-[#E8DDD3]"}`} />}
                </div>
                <div className="flex flex-col pb-3.5">
                  <span className={`text-[13px] ${done ? "font-bold" : "font-medium text-[#8A7769]"} ${warn ? "text-[#9B1239]" : ""}`}>
                    {warn ? "배송중 · 지연" : label}
                  </span>
                  <span className="text-xs tabular-nums text-[#6E5B50]">
                    {done && at ? fmt(at) : canceled ? "취소로 진행 안 함" : "대기"}
                  </span>
                  {i === 2 && o.courier && (
                    <span className="text-xs font-medium tabular-nums text-[#1D4B85]">{o.courier} {o.trackingNo}</span>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
        {canceled && (
          <p className="text-xs font-medium text-[#5F5550]">주문취소 · {fmt(timeOf("주문취소") ?? o.orderedAt)}</p>
        )}
      </div>

      {/* 처리 */}
      <div className="flex flex-col gap-2.5 px-5 pb-5 pt-4">
        {can("상품준비중") && (
          <button type="button" disabled={busy} className={primary} onClick={() => run({ status: "상품준비중" })}>상품 준비 시작</button>
        )}

        {can("배송중") && o.status === "상품준비중" && (
          <>
            <div className="grid grid-cols-[120px_1fr] gap-2">
              <label className="sr-only" htmlFor="admin-courier">택배사</label>
              <select
                id="admin-courier"
                value={courier}
                onChange={(e) => setCourier(e.target.value)}
                className="h-11 rounded-xl border border-[#E3D5CA] bg-white px-2 text-[13px] outline-none focus:border-brand"
              >
                {COURIERS.map((c) => <option key={c}>{c}</option>)}
              </select>
              <label className="sr-only" htmlFor="admin-tracking">운송장 번호</label>
              <input
                id="admin-tracking"
                value={trackingNo}
                onChange={(e) => setTrackingNo(e.target.value)}
                placeholder="운송장 번호 (숫자와 -)"
                inputMode="numeric"
                maxLength={30}
                className="h-11 min-w-0 rounded-xl border border-[#E3D5CA] px-3 text-[13px] tabular-nums outline-none focus:border-brand"
              />
            </div>
            <button
              type="button"
              disabled={busy}
              className={primary}
              onClick={() => run({ status: "배송중", courier, trackingNo: trackingNo.trim() || undefined })}
            >
              출고 처리 (배송중으로 변경)
            </button>
          </>
        )}

        {can("배송완료") && (
          <button type="button" disabled={busy} className={primary} onClick={() => run({ status: "배송완료" })}>배송완료로 변경</button>
        )}

        {(can("배송지연") || can("주문취소")) && (
          <>
            <label className="text-xs font-bold text-[#6E5B50]" htmlFor="admin-note">
              사유 <span className="font-medium">(배송 지연 · 주문 취소 때 꼭 적어 주세요)</span>
            </label>
            <textarea
              id="admin-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={300}
              rows={2}
              placeholder="예: 택배사 물량 증가로 하루 늦어져요"
              className="resize-none rounded-xl border border-[#E3D5CA] px-3 py-2 text-[13px] outline-none focus:border-brand"
            />
          </>
        )}

        <div className="flex gap-2 empty:hidden">
          {can("배송중") && delayed && (
            <button type="button" disabled={busy} className={secondary} onClick={() => run({ status: "배송중" })}>배송 재개 (배송중으로)</button>
          )}
          {can("배송지연") && (
            <button type="button" disabled={busy} className={secondary} onClick={() => run({ status: "배송지연", note: reason })}>배송 지연으로 표시</button>
          )}
          {can("주문취소") && (
            <button
              type="button"
              disabled={busy}
              className={secondary}
              onClick={() => {
                if (confirm(`#${o.orderId} 주문을 취소할까요? 재고가 돌아오고 결제는 결제취소가 돼요.`)) run({ status: "주문취소", note: reason });
              }}
            >
              주문 취소
            </button>
          )}
        </div>

        {o.nextStatuses.length === 0 && (
          <button type="button" disabled className="h-12 w-full cursor-not-allowed rounded-xl bg-[#EDE6E0] text-[15px] font-bold text-[#6E5B50]">
            {canceled ? "취소된 주문이에요" : "처리가 끝난 주문이에요"}
          </button>
        )}

        {error && (
          <p role="alert" className="rounded-[10px] bg-[#FCE3EB] px-3 py-2.5 text-center text-[13px] font-medium text-[#9B1239]">
            {error}
          </p>
        )}

        <p className="text-center text-xs text-[#6E5B50]">바꾼 상태는 서버에 저장되고, 누가 언제 바꿨는지 이력에 남아요.</p>
      </div>
    </aside>
  );
}
