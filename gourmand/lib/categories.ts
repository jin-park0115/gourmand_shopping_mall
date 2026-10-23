// 과자 종류별 카테고리 (화면 꾸밈용: 이름 · 소개 · 대표 사진)
// 어떤 상품이 어느 카테고리인지는 DB 가 정해요 (상품의 categorySlug, 시드: backend/src/infrastructure/seed.py).
// 카테고리별 상품 수는 GET /categories (lib/products.ts fetchCategoryCounts)
export interface Category {
  slug: string; // 주소: /category/snack (DB category.slug 와 같아요)
  name: string;
  desc: string; // 한 줄 소개
  image: string; // 대표 사진
}

export const CATEGORIES: Category[] = [
  {
    slug: "snack",
    name: "스낵·칩",
    desc: "감자·옥수수·쌀로 만든 바삭한 스낵",
    image: "/images/products/1.webp",
  },
  {
    slug: "cookie",
    name: "쿠키·비스킷",
    desc: "오레오부터 버터 비스킷까지",
    image: "/images/products/41.webp",
  },
  {
    slug: "bakery",
    name: "케이크·베이커리",
    desc: "도쿄바나나·펑리수·마들렌",
    image: "/images/products/4.webp",
  },
  {
    slug: "chocolate",
    name: "초콜릿",
    desc: "생초콜릿부터 초코 과자까지",
    image: "/images/products/7.webp",
  },
  {
    slug: "candy",
    name: "젤리·캔디",
    desc: "하리보·곤약젤리·밀크 캔디",
    image: "/images/products/58.webp",
  },
  {
    slug: "savory",
    name: "육포·견과·별미",
    desc: "육포, 해바라기씨, 말린 과일",
    image: "/images/products/22.webp",
  },
];

export const getCategory = (slug: string) => CATEGORIES.find((c) => c.slug === slug);
