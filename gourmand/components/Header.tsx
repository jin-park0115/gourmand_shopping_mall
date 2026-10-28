"use client";

import Link from "next/link";
import { Suspense } from "react";
import { usePathname, useRouter } from "next/navigation";
import CartBadge from "@/components/CartBadge";
import SearchField from "@/components/SearchField";
import { useAuth } from "@/components/AuthProvider";
import { askLogin, loginHref } from "@/lib/api";

// 로그인 · 로그아웃 (토큰 확인 전에는 아무것도 안 보여서 깜빡이지 않아요)
// 지금 주소(usePathname)를 읽어서 Suspense 안에 둬요 (Next 16 cacheComponents 규칙)
function AuthMenu(props: { className: string }) {
  return (
    <Suspense fallback={null}>
      <AuthMenuInner {...props} />
    </Suspense>
  );
}

function AuthMenuInner({ className }: { className: string }) {
  const { member, ready, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  if (!ready) return null;

  if (!member) {
    return (
      <Link href={loginHref(pathname)} className={className}>
        로그인
      </Link>
    );
  }
  // 로그아웃하면 홈으로 (마이페이지 · 장바구니처럼 로그인해야 보이는 화면에 빈 안내만 남지 않게)
  const onLogout = async () => {
    await logout();
    router.replace("/");
  };
  return (
    <>
      {/* 관리자가 쇼핑몰 화면을 보다가 관리자 화면으로 돌아갈 수 있게 */}
      {member.role === "admin" && (
        <Link href="/admin" className={className}>
          관리자
        </Link>
      )}
      <button type="button" onClick={onLogout} className={className} title={`${member.name}님 로그아웃`}>
        로그아웃
      </button>
    </>
  );
}

const countries = [
  { name: "일본", slug: "japan" },
  { name: "대만", slug: "taiwan" },
  { name: "중국", slug: "china" },
  { name: "베트남", slug: "vietnam" },
  { name: "그 외", slug: "other" },
];

// 돋보기 아이콘
function SearchIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      viewBox="0 0 24 24"
    >
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </svg>
  );
}

// PC 헤더 검색창 (모바일은 하단 '검색' 탭 사용)
function SearchBox() {
  return (
    <form
      action="/products"
      role="search"
      className="relative flex h-11 w-full items-center rounded-full border border-brand-line bg-brand-soft pl-4 pr-1 transition focus-within:border-brand focus-within:bg-white focus-within:ring-2 focus-within:ring-brand-soft"
    >
      <SearchField
        searchPath="/products"
        panelClassName="right-0 w-[440px] max-w-[calc(100vw-2rem)]"
        placeholder="어떤 간식을 찾으세요?"
        className="w-full bg-transparent text-[15px] text-gray-900 outline-none placeholder:text-slate-500"
      />

      <button
        type="submit"
        aria-label="검색"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-brand shadow-sm transition hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
      >
        <SearchIcon />
      </button>
    </form>
  );
}

// PC 나라 메뉴 링크
function CountryLinks({ current }: { current: string | null }) {
  // current: 지금 보고 있는 나라 slug (모르면 null)
  return (
    <>
      {countries.map((country) => {
        const active = current === country.slug;
        return (
          <Link
            key={country.slug}
            href={`/country/${country.slug}`}
            aria-current={active ? "page" : undefined}
            className={`border-b-2 py-1 text-[17px] font-semibold transition hover:text-brand ${
              active ? "border-brand text-brand" : "border-transparent text-gray-700"
            }`}
          >
            {country.name}
          </Link>
        );
      })}
    </>
  );
}

// 현재 주소를 읽어서 강조 (주소는 접속 시점에만 알 수 있어 Suspense 안에서만 사용)
function ActiveCountryLinks() {
  const pathname = usePathname();
  const current = pathname.startsWith("/country/")
    ? pathname.split("/")[2]
    : null;
  return <CountryLinks current={current} />;
}

export default function Header() {
  const { member, ready } = useAuth();
  return (
    <header data-shop-chrome className="sticky top-0 z-50 border-b border-gray-200 bg-white">
      {/* PC 헤더 */}
      <div className="mx-auto hidden h-20 max-w-6xl items-center gap-5 px-4 lg:flex xl:gap-8">
        {/* 로고 */}
        <Link href="/" className="shrink-0">
          <img
            src="/images/common/logo.webp"
            alt="구르망 GOURMAND"
            className="h-20 w-auto"
          />
        </Link>

        {/* 국가별 메뉴 */}
        <nav
          aria-label="국가별 상품"
          className="flex shrink-0 items-center gap-4 whitespace-nowrap xl:gap-6"
        >
          {/* 미리 만들어 둔 화면에는 강조 없이, 접속 후 현재 나라를 강조 */}
          <Suspense fallback={<CountryLinks current={null} />}>
            <ActiveCountryLinks />
          </Suspense>
        </nav>

        {/* 검색창 */}
        <div className="ml-auto min-w-0 max-w-64 flex-1">
          <SearchBox />
        </div>

        {/* 장바구니 · 마이페이지 */}
        <div className="flex shrink-0 items-center gap-5 whitespace-nowrap">
          <Link
            href="/cart"
            onClick={(e) => {
              // 비회원이면 장바구니 화면 대신 로그인 안내 창을 띄워요
              if (ready && !member) {
                e.preventDefault();
                askLogin("/cart");
              }
            }}
            className="flex flex-col items-center gap-1 text-[13px] font-medium text-gray-700 transition hover:text-brand"
          >
            <span className="relative">
              <img
                src="/images/common/cart_icon.png"
                alt=""
                className="h-7 w-7"
              />
              <CartBadge />
            </span>
            <span>장바구니</span>
          </Link>

          <Link
            href="/mypage"
            className="flex flex-col items-center gap-1 text-[13px] font-medium text-gray-700 transition hover:text-brand"
          >
            <img
              src="/images/common/my_page_icon.png"
              alt=""
              className="h-7 w-7"
            />
            <span>마이페이지</span>
          </Link>

          <AuthMenu className="rounded-full border border-gray-200 px-3.5 py-1.5 text-[13px] font-semibold text-gray-700 transition hover:border-brand-line hover:text-brand" />
        </div>
      </div>

      {/* 모바일 헤더: 가운데 로고 + 오른쪽 로그인/로그아웃 (메뉴·검색·장바구니는 하단 탭에서) */}
      <div className="relative flex h-14 items-center justify-center px-3 lg:hidden">
        <Link href="/">
          <img
            src="/images/common/logo.webp"
            alt="구르망 GOURMAND"
            className="h-10 w-auto"
          />
        </Link>
        <div className="absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-3">
          <AuthMenu className="text-[13px] font-semibold text-gray-600" />
        </div>
      </div>
    </header>
  );
}
