"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { API_URL } from "@/lib/api";

// 검색창 + 자동완성 (GET /products/suggest). 치는 동안 맞는 카테고리 · 나라 · 상품을 바로 아래에 보여 줘요.
// 규칙(자모 · 초성 · 동의어)은 서버 검색과 같아서 "ㄱㅇ" 만 쳐도 곤약젤리가 떠요.
// 키보드: ↑↓ 로 고르고 Enter 로 이동, Esc 로 닫기. 고른 게 없으면 Enter 는 원래대로 검색 결과 화면으로 가요.

type Suggest = {
  q: string; // 이 결과가 어떤 검색어의 것인지 (늦게 온 옛 결과를 안 보여 주려고)
  total: number;
  products: { id: number; name: string; imageUrl: string; price: number; salePrice: number; isSoldOut: boolean }[];
  categories: { slug: string; name: string; productCount: number }[];
  countries: { slug: string; name: string }[];
};

type Option = { href: string; kind: "category" | "country" | "product" | "all"; data: unknown };

const WAIT_MS = 200; // 치기를 멈춘 뒤 이만큼 기다렸다가 물어봐요

// 검색어와 같은 글자는 굵게 (자모 · 초성으로 찾은 경우는 그대로)
function Highlight({ text, q }: { text: string; q: string }) {
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (!q || i < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, i)}
      <strong className="font-bold text-brand">{text.slice(i, i + q.length)}</strong>
      {text.slice(i + q.length)}
    </>
  );
}

export default function SearchField({
  searchPath,
  defaultValue = "",
  className,
  placeholder,
  autoFocus,
  panelClassName = "inset-x-0",
}: {
  searchPath: string; // 전체 결과 화면 (/products 또는 /search)
  defaultValue?: string;
  className: string;
  placeholder: string;
  autoFocus?: boolean;
  panelClassName?: string; // 제안 목록 위치 · 너비 (좁은 헤더 검색창은 더 넓게 펼쳐요)
}) {
  const router = useRouter();
  const listId = useId();
  const [value, setValue] = useState(defaultValue);
  const [result, setResult] = useState<Suggest | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const q = value.trim();

  useEffect(() => {
    if (!q) return;
    const abort = new AbortController(); // 더 쳤으면 이전 요청은 버려요
    const timer = setTimeout(() => {
      fetch(`${API_URL}/products/suggest?${new URLSearchParams({ q: q.slice(0, 50) })}`, { signal: abort.signal })
        .then((res) => (res.ok ? res.json() : null))
        .then((body) => {
          if (!body) return;
          setResult({ ...body, q });
          setActive(-1);
        })
        .catch(() => {}); // 자동완성은 보조 기능이라 실패하면 조용히 안 보여 줘요
    }, WAIT_MS);
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [q]);

  const current = result && q && result.q === q ? result : null;
  const options: Option[] = current
    ? [
        ...current.categories.map((c) => ({ href: `/category/${c.slug}`, kind: "category" as const, data: c })),
        ...current.countries.map((c) => ({ href: `/country/${c.slug}`, kind: "country" as const, data: c })),
        ...current.products.map((p) => ({ href: `/products/${p.id}`, kind: "product" as const, data: p })),
        ...(current.total > 0 ? [{ href: `${searchPath}?q=${encodeURIComponent(q)}`, kind: "all" as const, data: null }] : []),
      ]
    : [];
  const shown = open && current !== null;
  const optionId = (i: number) => `${listId}-${i}`;

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      // 목록이 열려 있으면 목록만 닫아요 (검색창의 기본 동작인 '글자 지우기'는 막아요). 닫혀 있으면 원래대로 지워져요
      if (shown) e.preventDefault();
      return setOpen(false);
    }
    if (!options.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      // -1 = 검색창(고른 것 없음). 맨 끝에서 더 가면 검색창으로 돌아와요
      const last = options.length - 1;
      setActive((i) => (e.key === "ArrowDown" ? (i >= last ? -1 : i + 1) : i <= -1 ? last : i - 1));
      return;
    }
    if (e.key === "Enter" && shown && active >= 0 && active < options.length) {
      e.preventDefault(); // 고른 제안으로 바로 이동 (검색 결과 화면 대신)
      go(options[active].href);
    }
  };

  const optionClass = (i: number) =>
    `flex items-center gap-3 px-4 py-2.5 text-sm text-gray-800 ${active === i ? "bg-brand-soft" : "hover:bg-gray-50"}`;

  return (
    <div
      className="min-w-0 flex-1"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false); // 제안을 누르는 중이면 닫지 않아요
      }}
    >
      <input
        type="search"
        name="q"
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        autoFocus={autoFocus}
        autoComplete="off"
        aria-label="간식 검색"
        placeholder={placeholder}
        role="combobox"
        aria-expanded={shown}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={shown && active >= 0 ? optionId(active) : undefined}
        className={className}
      />

      {shown && (
        <div
          // 누르는 순간 검색창 포커스가 빠지지 않게 해요. Safari 는 링크를 눌러도 링크에 포커스를 주지 않아서,
          // 이게 없으면 blur 로 목록이 먼저 닫히고 클릭이 사라져요 (Chrome 은 링크로 포커스가 가서 괜찮았어요)
          onMouseDown={(e) => e.preventDefault()}
          className={`absolute top-full z-50 mt-2 ${panelClassName} overflow-hidden rounded-2xl border border-gray-200 bg-white text-left shadow-xl`}
        >
          {options.length === 0 ? (
            <p className="px-4 py-4 text-sm text-gray-500">‘{q}’에 맞는 간식이 아직 없어요.</p>
          ) : (
            <ul id={listId} role="listbox" aria-label="검색어 제안" className="max-h-[70vh] overflow-y-auto py-1">
              {options.map((o, i) => (
                <li key={o.href} id={optionId(i)} role="option" aria-selected={active === i}>
                  <Link href={o.href} onClick={() => setOpen(false)} onMouseEnter={() => setActive(i)} className={optionClass(i)}>
                    {o.kind === "category" && (() => {
                      const c = o.data as Suggest["categories"][number];
                      return (
                        <>
                          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-semibold text-gray-600">카테고리</span>
                          <Highlight text={c.name} q={q} />
                          <span className="text-xs text-gray-400">{c.productCount}개</span>
                        </>
                      );
                    })()}
                    {o.kind === "country" && (() => {
                      const c = o.data as Suggest["countries"][number];
                      return (
                        <>
                          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-semibold text-gray-600">나라</span>
                          <Highlight text={c.name} q={q} />
                          {c.slug === "other" && <span className="text-xs text-gray-400">그 외</span>}
                        </>
                      );
                    })()}
                    {o.kind === "product" && (() => {
                      const p = o.data as Suggest["products"][number];
                      return (
                        <>
                          <img src={p.imageUrl} alt="" className="h-10 w-10 shrink-0 rounded-md border border-gray-100 object-contain" />
                          <span className="min-w-0 flex-1 truncate">
                            <Highlight text={p.name} q={q} />
                          </span>
                          {p.isSoldOut ? (
                            <span className="shrink-0 text-xs font-semibold text-gray-400">품절</span>
                          ) : (
                            <span className="shrink-0 font-semibold text-gray-900">{p.salePrice.toLocaleString()}원</span>
                          )}
                        </>
                      );
                    })()}
                    {o.kind === "all" && (
                      <span className="font-semibold text-brand">
                        ‘{q}’ 전체 결과 {current!.total}개 보기 ›
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
