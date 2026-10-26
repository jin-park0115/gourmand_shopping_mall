// 백엔드 API 호출 (FastAPI, 기본 http://localhost:8000)
// 오류 응답 { code, message } 를 ApiError 로 바꿔서 던져요. 화면은 message 를 그대로 보여 주면 돼요.
// 로그인 토큰이 있으면 Authorization 헤더에 자동으로 붙여요 (SCRUM-20).

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// ── 로그인 토큰 ──
// 토큰을 어디에 두는지는 이 세 함수만 알아요. httpOnly 쿠키로 바꾸면 여기와 백엔드 로그인만 고치면 돼요.
// ponytail: localStorage 는 화면에 악성 스크립트가 들어오면(XSS) 읽힐 수 있어요. 실서비스면 httpOnly 쿠키로.
const TOKEN_KEY = "gourmand-token";
export const AUTH_CHANGED = "gourmand-auth-changed"; // 로그인 · 로그아웃 때 AuthProvider 에 알리는 이벤트

export function getToken(): string | null {
  if (typeof window === "undefined") return null; // 서버 컴포넌트에는 토큰이 없어요 (공개 API 만 불러요)
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // 저장소를 못 쓰면 이번 화면에서만 로그인 상태가 없어요
  }
  window.dispatchEvent(new Event(AUTH_CHANGED));
}

// 로그인 화면으로 (돌아올 주소를 next 로)
export function loginHref(next?: string) {
  return next && next !== "/" ? `/login?next=${encodeURIComponent(next)}` : "/login";
}

// 비회원이 장바구니를 쓰려고 할 때: 로그인이 필요하다고 알리고, 확인하면 로그인 화면으로 (취소하면 그대로)
export function askLogin(next: string) {
  if (confirm("장바구니는 로그인한 회원만 쓸 수 있어요.\n로그인 화면으로 이동할까요?")) {
    location.assign(loginHref(next));
  }
}

export async function api<T>(
  path: string,
  init?: RequestInit,
  // false: 토큰이 만료돼도 로그인 화면으로 보내지 않아요 (헤더의 로그인 상태 확인처럼 조용히 확인할 때)
  { redirectOn401 = true }: { redirectOn401?: boolean } = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // 토큰을 보냈는데 401 = 만료 · 로그아웃된 토큰. 비밀번호가 틀린 로그인 401 은 토큰이 없어서 여기 안 와요
    if (res.status === 401 && token) {
      setToken(null);
      if (redirectOn401 && !location.pathname.startsWith("/login")) {
        location.assign(loginHref(location.pathname + location.search));
      }
    }
    throw new ApiError(res.status, body.code ?? "HTTP_ERROR", body.message ?? `요청에 실패했어요. (${res.status})`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

// 페이지 응답 (백엔드 presentation/schemas.py Page)
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
