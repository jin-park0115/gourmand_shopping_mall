// 컴포넌트 테스트용 next/navigation · next/link 대역 (앱 라우터 없이 그리려고)
import { vi } from "vitest";

export const router = { push: vi.fn(), replace: vi.fn() };
export const searchParams = { value: new URLSearchParams() };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => searchParams.value,
  usePathname: () => "/",
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
