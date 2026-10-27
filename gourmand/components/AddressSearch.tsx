"use client";

import { useCallback, useRef } from "react";

// 도로명 주소 찾기 (카카오 우편번호 서비스, 무료 · 키 없음). 스크립트는 처음 [주소 검색]을 누를 때만 불러와요.
// 새 창(팝업) 대신 화면 안의 창에 넣어요 (모바일 · 팝업 차단에서 깨지지 않게). 휴대폰에서는 화면 가득
// https://postcode.map.kakao.com/guide

export const POSTCODE_SCRIPT = "https://t1.kakaocdn.net/mapjs/postcode/prod/postcode.v2.js";

// 쓰는 값만 (전체 목록은 위 가이드)
type PostcodeResult = {
  zonecode: string; // 새 우편번호 5자리
  userSelectedType: "R" | "J"; // 도로명(R) · 지번(J) 중 사용자가 누른 것
  roadAddress: string;
  jibunAddress: string;
  bname: string; // 법정동 (예: 역삼동)
  buildingName: string;
  apartment: "Y" | "N";
};

declare global {
  interface Window {
    daum?: {
      Postcode: new (options: {
        oncomplete: (data: PostcodeResult) => void;
        width?: string;
        height?: string;
      }) => { embed: (element: HTMLElement) => void };
    };
  }
}

let loading: Promise<void> | null = null;

function loadPostcode(): Promise<void> {
  if (window.daum?.Postcode) return Promise.resolve();
  loading ??= new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = POSTCODE_SCRIPT;
    script.async = true;
    script.onload = () => (window.daum?.Postcode ? resolve() : reject(new Error("postcode")));
    script.onerror = () => reject(new Error("postcode"));
    document.head.appendChild(script);
  }).catch((e) => {
    loading = null; // 다음에 누르면 다시 시도
    throw e;
  });
  return loading;
}

// 도로명 주소 뒤에 (동, 건물명)을 붙여요. 카카오 가이드의 '참고항목' 규칙
export function formatAddress(d: PostcodeResult): string {
  if (d.userSelectedType === "J") return d.jibunAddress;
  const extra = [
    /[동로가]$/.test(d.bname) ? d.bname : "",
    d.buildingName && d.apartment === "Y" ? d.buildingName : "",
  ].filter(Boolean);
  return extra.length ? `${d.roadAddress} (${extra.join(", ")})` : d.roadAddress;
}

// 주소 검색 창과 여는 함수. 고르면 onSelect(우편번호, 주소), 스크립트를 못 불러오면 onUnavailable
export function useAddressSearch({
  onSelect,
  onUnavailable,
}: {
  onSelect: (zipcode: string, address: string) => void;
  onUnavailable: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const box = useRef<HTMLDivElement>(null);

  const open = useCallback(async () => {
    dialog.current?.showModal();
    try {
      await loadPostcode();
    } catch {
      dialog.current?.close();
      onUnavailable();
      return;
    }
    if (!box.current || !window.daum) return;
    box.current.replaceChildren(); // 다시 열면 처음 검색 화면부터
    new window.daum.Postcode({
      width: "100%",
      height: "100%",
      oncomplete: (data) => {
        dialog.current?.close();
        onSelect(data.zonecode, formatAddress(data));
      },
    }).embed(box.current);
  }, [onSelect, onUnavailable]);

  const element = (
    <dialog
      ref={dialog}
      aria-label="주소 검색"
      onClick={(e) => e.target === e.currentTarget && dialog.current?.close()}
      className="m-0 h-dvh max-h-none w-full max-w-none p-0 backdrop:bg-black/40 sm:m-auto sm:h-[560px] sm:max-w-lg sm:rounded-2xl sm:shadow-xl"
    >
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <p className="font-bold text-gray-900">주소 검색</p>
          <button
            type="button"
            onClick={() => dialog.current?.close()}
            aria-label="닫기"
            className="h-8 w-8 rounded-full text-xl leading-none text-gray-500 hover:bg-gray-100"
          >
            ×
          </button>
        </div>
        <div ref={box} className="min-h-0 flex-1">
          <p className="p-6 text-center text-sm text-gray-500">주소 검색을 불러오는 중이에요…</p>
        </div>
      </div>
    </dialog>
  );

  return { open, element };
}
