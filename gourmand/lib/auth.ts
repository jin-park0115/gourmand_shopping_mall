// 회원가입 · 로그인 · 로그아웃 · 내 정보 (백엔드 /auth, SCRUM-18 · 19)
import { api, setToken } from "@/lib/api";

export interface Member {
  id: number;
  email: string;
  name: string;
  phone: string | null;
  role: "customer" | "admin";
}

export interface SignupInput {
  email: string;
  password: string;
  name: string;
  phone?: string;
}

// OAuth2 password 방식이라 JSON 이 아니라 form 으로 보내고, 이메일은 username 칸에 넣어요
// 로그인한 회원을 돌려줘요 (역할에 따라 갈 화면이 달라서)
export async function login(email: string, password: string): Promise<Member> {
  const res = await api<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: new URLSearchParams({ username: email, password }),
  });
  setToken(res.access_token);
  return fetchMe();
}

// 가입하면 바로 로그인해요
export async function signup(input: SignupInput): Promise<Member> {
  await api<Member>("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, phone: input.phone || null }),
  });
  return login(input.email, input.password);
}

// 서버 블랙리스트에 올려서 같은 토큰을 다시 못 쓰게 해요. 서버가 실패해도 이 브라우저에서는 로그아웃
export async function logout() {
  try {
    await api<void>("/auth/logout", { method: "POST" }, { redirectOn401: false });
  } catch {
    // 서버 오류 · 연결 실패여도 화면은 로그아웃한 다음 화면으로 넘어가야 해서 던지지 않아요
  } finally {
    setToken(null);
  }
}

export const fetchMe = () => api<Member>("/auth/me", undefined, { redirectOn401: false });

// 로그인 후 돌아갈 주소: 우리 사이트 안의 주소만 (외부 사이트로 보내지 않게).
// "//evil.com" 뿐 아니라 "/\evil.com" 도 브라우저는 "\" 를 "/" 로 읽어 다른 사이트로 가요.
// 그래서 글자 검사 대신 브라우저와 같은 규칙(URL)으로 해석해서 우리 주소인지 확인해요
const SAME_SITE = "https://gourmand.invalid";
export function safeNext(next: string | null) {
  if (!next || !next.startsWith("/")) return "/";
  try {
    const url = new URL(next, SAME_SITE);
    return url.origin === SAME_SITE ? url.pathname + url.search + url.hash : "/";
  } catch {
    return "/";
  }
}

// 로그인 후 갈 곳: 관리자는 관리자 화면, 고객은 원래 보던 주소
// 고객이 /admin 에서 왔으면 '관리자만' 안내만 보이니까 홈으로 보내요
export function afterLoginPath(role: Member["role"], next: string) {
  const toAdmin = next === "/admin" || next.startsWith("/admin/") || next.startsWith("/admin?");
  if (role === "admin") return toAdmin ? next : "/admin";
  return toAdmin ? "/" : next;
}
