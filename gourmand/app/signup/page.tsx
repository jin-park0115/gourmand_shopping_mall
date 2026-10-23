import { Suspense } from "react";

import { SignupForm } from "@/components/AuthForms";

export const metadata = { title: "회원가입 | 구르망" };

export default function SignupPage() {
  return (
    <main className="mx-auto max-w-sm px-4 py-12">
      <h1 className="mb-6 text-2xl font-extrabold text-[#2A1A12]">회원가입</h1>
      <Suspense fallback={null}>
        <SignupForm />
      </Suspense>
    </main>
  );
}
