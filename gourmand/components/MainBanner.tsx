"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";

const banners = [
  {
    id: 1,
    country: "희주 PICK",
    image: "/images/common/banner_heeju.webp",
    href: "/pick/heeju",
  },
  {
    id: 2,
    country: "예주 PICK",
    image: "/images/common/banner_yeju.webp",
    href: "/pick/yeju",
  },
  {
    id: 3,
    country: "종복 PICK",
    image: "/images/common/banner_jongbok.webp",
    href: "/pick/jongbok",
  },
  {
    id: 4,
    country: "강 PICK",
    image: "/images/common/banner_gang.webp",
    href: "/pick/gang",
  },
  {
    id: 5,
    country: "지아 PICK",
    image: "/images/common/banner_jina.webp",
    href: "/pick/jia",
  },
];

export default function MainBanner() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const nextBanner = () => {
    setCurrentIndex((prev) => (prev + 1) % banners.length);
  };

  const prevBanner = () => {
    setCurrentIndex(
      (prev) => (prev - 1 + banners.length) % banners.length
    );
  };

  return (
    <section
      aria-label="구르망 추천 간식 배너"
      className="w-full"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onFocusCapture={() => setIsPaused(true)}
      onBlurCapture={() => setIsPaused(false)}
    >
      {/* 배너 이미지: 원본 비율(16:9)을 살려 모바일에서도 잘리지 않게 */}
      <div className="group relative aspect-[16/9] overflow-hidden rounded-2xl bg-brand-soft shadow-md lg:aspect-[2/1]">
        {banners.map((banner, index) => (
          <div
            key={banner.id}
            aria-hidden={index !== currentIndex}
            className={`absolute inset-0 transition-opacity duration-700 ease-in-out ${
              index === currentIndex
                ? "z-10 opacity-100"
                : "pointer-events-none z-0 opacity-0"
            }`}
          >
            <Link
              href={banner.href}
              tabIndex={index === currentIndex ? 0 : -1}
              className="absolute inset-0 block"
            >
              <Image
                src={banner.image}
                alt={`${banner.country} 추천 간식 배너`}
                fill
                sizes="(max-width: 1152px) 100vw, 1152px"
                className="object-cover object-center"
                priority={index === 0}
              />
            </Link>
          </div>
        ))}

        {/* 이전 · 다음 버튼 (데스크톱은 마우스를 올렸을 때만 표시) */}
        <button
          type="button"
          onClick={prevBanner}
          aria-label="이전 배너"
          className="absolute left-3 top-1/2 z-20 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/80 text-xl text-brand shadow transition hover:bg-white focus-visible:opacity-100 sm:h-11 sm:w-11 sm:text-2xl lg:opacity-0 lg:group-hover:opacity-100"
        >
          ‹
        </button>
        <button
          type="button"
          onClick={nextBanner}
          aria-label="다음 배너"
          className="absolute right-3 top-1/2 z-20 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/80 text-xl text-brand shadow transition hover:bg-white focus-visible:opacity-100 sm:h-11 sm:w-11 sm:text-2xl lg:opacity-0 lg:group-hover:opacity-100"
        >
          ›
        </button>

        {/* 현재 위치 (모바일 전용, 오른쪽 아래 작게) */}
        <span className="absolute bottom-2.5 right-2.5 z-20 rounded-full bg-black/40 px-2.5 py-0.5 text-xs font-medium text-white sm:hidden">
          {currentIndex + 1} / {banners.length}
        </span>
      </div>

      {/* 배너 아래 탭: 그림을 가리지 않고, 진행 막대로 넘어갈 시간을 표시 */}
      <div className="mt-3 hidden grid-cols-5 gap-2 sm:grid">
        {banners.map((banner, index) => {
          const isActive = currentIndex === index;
          return (
            <button
              key={banner.id}
              type="button"
              onClick={() => setCurrentIndex(index)}
              aria-label={`${banner.country} 배너 보기`}
              aria-current={isActive ? "true" : undefined}
              className={`group/tab text-left text-sm font-semibold transition ${
                isActive ? "text-brand" : "text-gray-400 hover:text-gray-700"
              }`}
            >
              <span className="relative block h-1 overflow-hidden rounded-full bg-gray-200">
                {isActive && (
                  <span
                    key={currentIndex}
                    onAnimationEnd={nextBanner}
                    className="banner-progress absolute inset-y-0 left-0 rounded-full bg-brand"
                    style={{ animationPlayState: isPaused ? "paused" : "running" }}
                  />
                )}
              </span>
              <span className="mt-2 block">{banner.country}</span>
            </button>
          );
        })}
      </div>

      {/* 모바일: 탭 대신 자동 넘김 타이머만 (화면에는 보이지 않음) */}
      <span
        key={`m-${currentIndex}`}
        aria-hidden="true"
        onAnimationEnd={nextBanner}
        className="banner-progress block h-0 sm:hidden"
        style={{ animationPlayState: isPaused ? "paused" : "running" }}
      />
    </section>
  );
}
