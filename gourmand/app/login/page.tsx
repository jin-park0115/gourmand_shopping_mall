import { Suspense } from "react";

import { LoginForm } from "@/components/AuthForms";

export const metadata = { title: "로그인 | 구르망" };

// 로그인 (/login?next=/cart 처럼 돌아갈 주소를 받아요)
export default function LoginPage() {
  return (
    <main className="mx-auto max-w-sm px-4 py-12">
      <h1 className="mb-6 text-2xl font-extrabold text-[#2A1A12]">로그인</h1>
      {/* 주소의 next 를 읽는 폼이라 Suspense 안에 둬요 */}
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
