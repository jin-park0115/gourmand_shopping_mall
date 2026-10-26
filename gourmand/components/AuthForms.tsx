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

type FieldProps = {
  label: string;
  hint?: string;
  error?: string | null; // 이 칸 아래에 빨갛게
  ok?: string | null; // 이 칸 아래에 초록으로 (비밀번호 일치)
  children?: React.ReactNode; // 입력칸 오른쪽 안에 넣을 버튼
} & React.InputHTMLAttributes<HTMLInputElement>;

function Field({ label, hint, error, ok, children, ...input }: FieldProps) {
  return (
    <label className="block text-sm font-medium text-gray-700">
      {label}
      <span className="relative block">
        <input
          className={`${inputClass} ${children ? "pr-16" : ""} ${error ? "border-red-400" : ""}`}
          aria-invalid={error ? true : undefined}
          {...input}
        />
        {children}
      </span>
      {error ? (
        <span role="alert" className="mt-1 block text-xs text-red-600">{error}</span>
      ) : ok ? (
        <span className="mt-1 block text-xs text-[#2f7d5b]">{ok}</span>
      ) : (
        hint && <span className="mt-1 block text-xs text-gray-500">{hint}</span>
      )}
    </label>
  );
}

type SignupField = "email" | "password" | "name" | "phone";
const FIELD_WORDS: Record<SignupField, string[]> = {
  email: ["email", "이메일"],
  password: ["password", "비밀번호"],
  name: ["name", "이름"],
  phone: ["phone", "연락처"],
};

// 서버 메시지가 어느 칸 얘기인지 ("email: 이메일 형식이…", "이미 가입된 이메일이에요." → email). 모르면 null
function fieldOf(message: string): { field: SignupField | null; text: string } {
  const prefixed = /^(\w+): (.*)$/.exec(message); // 422 형식 오류는 "필드: 문장"
  const text = prefixed ? prefixed[2] : message;
  const head = prefixed ? prefixed[1] : message;
  const field = (Object.keys(FIELD_WORDS) as SignupField[]).find((f) => FIELD_WORDS[f].some((w) => head.includes(w)));
  return { field: field ?? null, text };
}

// 010-1234-5678 · 02-123-4567 처럼 하이픈을 넣어요 (숫자만 남겨서 다시 나눠요)
export function formatPhone(value: string): string {
  const d = value.replace(/\D/g, "").slice(0, 11);
  const area = d.startsWith("02") ? 2 : 3; // 서울 02 만 두 자리
  const rest = d.slice(area);
  if (!rest) return d;
  if (rest.length <= 4) return `${d.slice(0, area)}-${rest}`;
  const mid = rest.length === 7 ? 3 : 4; // 가운데: 7자리 남으면 3 (010-123-4567), 아니면 4
  return `${d.slice(0, area)}-${rest.slice(0, mid)}-${rest.slice(mid)}`;
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
  return { next, error, pending, onSubmit, clearError: () => setError(null) };
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
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [phone, setPhone] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const { next, error, pending, onSubmit, clearError } = useSubmit((f) =>
    signup({
      email: String(f.get("email")),
      password: String(f.get("password")),
      name: String(f.get("name")).trim(),
      phone: String(f.get("phone")).trim() || undefined,
    })
  );

  // 서버 오류는 해당 칸 아래에, 어느 칸인지 모르면 맨 아래 상자에
  const failed = error ? fieldOf(error) : null;
  const errorFor = (f: SignupField) => (failed?.field === f ? failed.text : null);
  const mismatch = confirm !== "" && confirm !== password;
  const passwordType = showPassword ? "text" : "password";
  // 칸을 고치면 그 칸의 서버 오류는 지워요
  const editing = (f: SignupField) => () => failed?.field === f && clearError();

  return (
    <form onSubmit={(e) => (mismatch ? e.preventDefault() : onSubmit(e))} className="space-y-4">
      {/* 길이 · 형식은 백엔드 규칙(domain/auth/member.py)과 같게 브라우저에서 먼저 확인해요 */}
      <Field
        label="이메일"
        name="email"
        type="email"
        autoComplete="email"
        required
        autoFocus
        error={errorFor("email")}
        onChange={editing("email")}
      />
      <Field
        label="비밀번호"
        name="password"
        type={passwordType}
        autoComplete="new-password"
        required
        minLength={8}
        maxLength={64}
        hint="8~64자"
        value={password}
        onChange={(e) => {
          setPassword(e.target.value);
          editing("password")();
        }}
        error={errorFor("password")}
      >
        <button
          type="button"
          onClick={() => setShowPassword((v) => !v)}
          aria-pressed={showPassword}
          className="absolute inset-y-0 right-2 my-auto h-8 rounded px-2 text-xs font-medium text-gray-500 hover:bg-gray-100"
        >
          {showPassword ? "숨기기" : "보기"}
        </button>
      </Field>
      <Field
        label="비밀번호 확인"
        name="passwordConfirm"
        type={passwordType}
        autoComplete="new-password"
        required
        maxLength={64}
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        error={mismatch ? "비밀번호가 달라요." : null}
        ok={confirm !== "" && !mismatch ? "비밀번호가 같아요 ✓" : null}
      />
      <Field
        label="이름"
        name="name"
        autoComplete="name"
        required
        maxLength={50}
        error={errorFor("name")}
        onChange={editing("name")}
      />
      <Field
        label="연락처 (선택)"
        name="phone"
        type="tel"
        inputMode="numeric"
        autoComplete="tel"
        pattern="[0-9\-]{9,20}"
        placeholder="010-1234-5678"
        value={phone}
        onChange={(e) => {
          setPhone(formatPhone(e.target.value));
          editing("phone")();
        }}
        error={errorFor("phone")}
      />
      <ErrorMessage message={failed && !failed.field ? failed.text : null} />
      <button type="submit" disabled={pending || mismatch} className={buttonClass}>
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
