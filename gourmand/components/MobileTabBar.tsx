'use client'; // 현재 주소(usePathname)를 읽어야 해서 클라이언트 컴포넌트로 선언

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import CartBadge from '@/components/CartBadge';
import { useAuth } from '@/components/AuthProvider';
import { askLogin } from '@/lib/api';

// 아이콘 공통 모양 (5개 모두 같은 굵기·크기의 선 아이콘으로 통일, 색은 글자색을 따라감)
function TabIcon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      className="h-6 w-6"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      viewBox="0 0 24 24"
    >
      {children}
    </svg>
  );
}

// 탭 목록: 이름, 이동할 주소, 강조할 주소 규칙, 아이콘
const tabs = [
  {
    label: '홈',
    href: '/',
    isActive: (path: string) => path === '/',
    icon: <path d="M3.5 10.5 12 4l8.5 6.5V19a1 1 0 0 1-1 1H15v-5.5H9V20H4.5a1 1 0 0 1-1-1z" />,
  },
  {
    label: '나라별',
    href: '/country/japan',
    // 어느 나라 페이지에 있든 '나라별' 탭을 강조
    isActive: (path: string) => path.startsWith('/country'),
    icon: (
      <>
        <circle cx="12" cy="12" r="8.5" />
        <path d="M3.5 12h17M12 3.5c2.3 2.4 3.4 5.2 3.4 8.5s-1.1 6.1-3.4 8.5c-2.3-2.4-3.4-5.2-3.4-8.5s1.1-6.1 3.4-8.5z" />
      </>
    ),
  },
  {
    label: '검색',
    href: '/search',
    // 검색 페이지 + 검색 결과(전체 상품) 페이지
    isActive: (path: string) => path === '/search' || path === '/products',
    icon: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 4.5 4.5" />
      </>
    ),
  },
  {
    label: '장바구니',
    href: '/cart',
    isActive: (path: string) => path === '/cart',
    icon: (
      <>
        <path d="M3 4.5h2.2l2.1 10.3a1 1 0 0 0 1 .8h8.9a1 1 0 0 0 1-.8l1.5-7.3H6" />
        <circle cx="9.5" cy="19" r="1.3" />
        <circle cx="16.5" cy="19" r="1.3" />
      </>
    ),
    badge: true, // 장바구니 수량 표시
  },
  {
    label: '마이페이지',
    href: '/mypage',
    isActive: (path: string) => path.startsWith('/mypage'),
    icon: (
      <>
        <circle cx="12" cy="8.5" r="3.8" />
        <path d="M4.5 20c.9-3.6 3.8-5.6 7.5-5.6s6.6 2 7.5 5.6" />
      </>
    ),
  },
];

// 모바일 하단 탭 메뉴 (lg 미만 화면에서만 보임)
export default function MobileTabBar() {
  const pathname = usePathname(); // 지금 보고 있는 페이지 주소 (예: '/', '/cart')
  const { member, ready } = useAuth();

  return (
    <nav
      data-shop-chrome
      aria-label="하단 메뉴"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-gray-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
    >
      <div className="flex h-16">
        {tabs.map((tab) => {
          const active = tab.isActive(pathname); // 지금 페이지와 같은 탭이면 강조
          return (
            <Link
              key={tab.label}
              href={tab.href}
              aria-current={active ? 'page' : undefined}
              onClick={(e) => {
                // 비회원이 장바구니 탭을 누르면 로그인 안내 창을 띄워요
                if (tab.href === '/cart' && ready && !member) {
                  e.preventDefault();
                  askLogin('/cart');
                }
              }}
              className={`flex flex-1 flex-col items-center justify-center gap-1 text-[11px] tracking-tight transition-colors ${
                active ? 'font-bold text-brand' : 'font-medium text-gray-500 active:text-brand'
              }`}
            >
              <span className="relative">
                <TabIcon>{tab.icon}</TabIcon>
                {tab.badge && <CartBadge />}
              </span>
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
