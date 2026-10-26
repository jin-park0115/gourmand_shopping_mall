"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { ApiError } from "@/lib/api";
import { afterLoginPath, login, safeNext, signup, type Member } from "@/lib/auth";

const inputClass =
  "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-brand";
const buttonClass =
  "mt-2 h-12 w-full rounded-xl bg-brand font-semibold text-white transition hover:bg-brand-dark disabled:opacity-60";

function Field({ label, hint, ...input }: { label: string; hint?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block text-sm font-medium text-gray-700">
      {label}
      <input className={inputClass} {...input} />
      {hint && <span className="mt-1 block text-xs text-gray-500">{hint}</span>}
    </label>
  );
}

// 제출 → 성공하면 관리자는 관리자 화면, 고객은 원래 보던 주소(next)로. 실패하면 서버 메시지를 그대로 보여 줘요
function useSubmit(action: (form: FormData) => Promise<Member>) {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const member = await action(new FormData(e.currentTarget));
      router.replace(afterLoginPath(member.role, next));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.");
      setPending(false);
    }
  };
  return { next, error, pending, onSubmit };
}

function ErrorMessage({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
      {message}
    </p>
  );
}

const withNext = (path: string, next: string) => (next === "/" ? path : `${path}?next=${encodeURIComponent(next)}`);

export function LoginForm() {
  const { next, error, pending, onSubmit } = useSubmit((f) => login(String(f.get("email")), String(f.get("password"))));

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Field label="이메일" name="email" type="email" autoComplete="email" required autoFocus />
      <Field label="비밀번호" name="password" type="password" autoComplete="current-password" required />
      <ErrorMessage message={error} />
      <button type="submit" disabled={pending} className={buttonClass}>
        {pending ? "로그인 중…" : "로그인"}
      </button>
      <p className="text-center text-sm text-gray-500">
        아직 회원이 아니에요?{" "}
        <Link href={withNext("/signup", next)} className="font-semibold text-brand hover:text-brand-dark">
          회원가입
        </Link>
      </p>
    </form>
  );
}

export function SignupForm() {
  const { next, error, pending, onSubmit } = useSubmit((f) =>
    signup({
      email: String(f.get("email")),
      password: String(f.get("password")),
      name: String(f.get("name")).trim(),
      phone: String(f.get("phone")).trim() || undefined,
    })
  );

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {/* 길이 · 형식은 백엔드 규칙(domain/auth/member.py)과 같게 브라우저에서 먼저 확인해요 */}
      <Field label="이메일" name="email" type="email" autoComplete="email" required autoFocus />
      <Field
        label="비밀번호"
        name="password"
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        maxLength={64}
        hint="8~64자"
      />
      <Field label="이름" name="name" autoComplete="name" required maxLength={50} />
      <Field
        label="연락처 (선택)"
        name="phone"
        type="tel"
        autoComplete="tel"
        pattern="[0-9\-]{9,20}"
        placeholder="010-1234-5678"
      />
      <ErrorMessage message={error} />
      <button type="submit" disabled={pending} className={buttonClass}>
        {pending ? "가입 중…" : "가입하고 로그인"}
      </button>
      <p className="text-center text-sm text-gray-500">
        이미 회원이에요?{" "}
        <Link href={withNext("/login", next)} className="font-semibold text-brand hover:text-brand-dark">
          로그인
        </Link>
      </p>
    </form>
  );
}
