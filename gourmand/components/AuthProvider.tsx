"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

import { AUTH_CHANGED, getToken } from "@/lib/api";
import { fetchMe, logout as logoutApi, type Member } from "@/lib/auth";

interface AuthContextValue {
  member: Member | null; // 로그인한 회원 (없으면 null)
  ready: boolean; // 저장된 토큰 확인이 끝났는지 (끝나기 전에는 로그인 · 로그아웃 버튼을 숨겨요)
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// 로그인 상태를 화면 전체에 알려 줘요. 토큰이 아직 유효한지는 GET /auth/me 로 확인해요
export function AuthProvider({ children }: { children: ReactNode }) {
  const [member, setMember] = useState<Member | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // 토큰이 아직 유효한지 서버에 물어봐요 (만료 · 로그아웃된 토큰이면 null). 상태는 응답이 온 뒤에 바꿔요
    const refresh = () => {
      (getToken() ? fetchMe().catch(() => null) : Promise.resolve(null)).then((me) => {
        setMember(me);
        setReady(true);
      });
    };
    refresh();
    // 로그인 · 로그아웃(이 탭)과 다른 탭에서 바뀐 토큰(storage)을 따라가요
    window.addEventListener(AUTH_CHANGED, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(AUTH_CHANGED, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  return <AuthContext.Provider value={{ member, ready, logout: logoutApi }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth는 AuthProvider 안에서만 쓸 수 있어요.");
  return ctx;
}
