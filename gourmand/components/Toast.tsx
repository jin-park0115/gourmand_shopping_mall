"use client";

import { createContext, useCallback, useContext, useState, ReactNode } from "react";

// 버튼 한 번으로 끝나는 동작의 결과를 잠깐 보여 줘요 ("리뷰를 삭제했어요" 같은 것).
// 폼 입력 오류는 토스트 대신 해당 칸 아래에 보여 주세요 (사라지면 무엇을 고칠지 놓쳐요).
type Kind = "success" | "error";
type Toast = { id: number; text: string; kind: Kind };

const ToastContext = createContext<((text: string, kind?: Kind) => void) | null>(null);
const SHOW_MS = 3000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((text: string, kind: Kind = "success") => {
    const id = Date.now() + Math.random();
    setToasts((list) => [...list.slice(-2), { id, text, kind }]); // 최대 3개
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), SHOW_MS);
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {/* 모바일은 하단 탭바 위, PC는 화면 아래 가운데 */}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-[60] flex flex-col items-center gap-2 px-4 lg:bottom-8"
      >
        {toasts.map((t) => (
          <p
            key={t.id}
            role={t.kind === "error" ? "alert" : "status"}
            className={`pointer-events-auto max-w-md rounded-xl px-4 py-3 text-sm font-medium text-white shadow-lg ${
              t.kind === "error" ? "bg-red-600" : "bg-gray-900/90"
            }`}
          >
            {t.text}
          </p>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const toast = useContext(ToastContext);
  if (!toast) throw new Error("useToast는 ToastProvider 안에서만 쓸 수 있어요.");
  return toast;
}
