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
export async function login(email: string, password: string) {
  const res = await api<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: new URLSearchParams({ username: email, password }),
  });
  setToken(res.access_token);
}

// 가입하면 바로 로그인해요
export async function signup(input: SignupInput) {
  await api<Member>("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, phone: input.phone || null }),
  });
  await login(input.email, input.password);
}

// 서버 블랙리스트에 올려서 같은 토큰을 다시 못 쓰게 해요. 서버가 실패해도 이 브라우저에서는 로그아웃
export async function logout() {
  try {
    await api<void>("/auth/logout", { method: "POST" }, { redirectOn401: false });
  } finally {
    setToken(null);
  }
}

export const fetchMe = () => api<Member>("/auth/me", undefined, { redirectOn401: false });

// 로그인 후 돌아갈 주소: 우리 사이트 안의 주소만 (//evil.com 같은 외부 주소로 보내지 않게)
export function safeNext(next: string | null) {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}
