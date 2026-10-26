import { api, ApiError, type Page } from "@/lib/api";
import { Product } from "@/types/product";
import { CATEGORIES } from "@/lib/categories";

// ── 상품 상태 ──
type Priced = Pick<Product, "price" | "discountPrice">;

export const isSoldOut = (p: Pick<Product, "isSoldOut" | "stock">) => p.isSoldOut || p.stock === 0;

// 할인가가 없으면 API 는 null 을 줘요 (null < 가격 은 true 라서 != null 로 꼭 먼저 확인)
export const hasDiscount = (p: Priced) =>
  p.discountPrice != null && p.discountPrice < p.price;

// 실제로 결제하는 가격 (할인가가 있으면 할인가)
export const salePrice = (p: Priced) =>
  hasDiscount(p) ? (p.discountPrice as number) : p.price;

export const discountRate = (p: Priced) =>
  hasDiscount(p) ? Math.round((1 - salePrice(p) / p.price) * 100) : 0;

// ── 나라 ──
export const COUNTRY_FILTERS = [
  { slug: "japan", name: "일본" },
  { slug: "taiwan", name: "대만" },
  { slug: "china", name: "중국" },
  { slug: "vietnam", name: "베트남" },
  { slug: "other", name: "그 외" },
];

// ── 카테고리 (lib/categories.ts의 6가지 과자 분류) ──
export const CATEGORY_FILTERS = CATEGORIES.map((c) => ({ slug: c.slug, name: c.name }));

// ── 정렬 ──
export const SORT_OPTIONS = [
  { slug: "recommend", name: "추천순" },
  { slug: "review", name: "리뷰 많은순" },
  { slug: "low", name: "낮은 가격순" },
  { slug: "high", name: "높은 가격순" },
  { slug: "new", name: "신상품순" },
];

export interface ProductQuery {
  q?: string;
  country?: string;
  category?: string;
  sort?: string;
}

// ── API (검색 · 필터 · 정렬은 서버가 해요: GET /products) ──

// 상품이 60개라 한 번에 100개까지 받아요. 상품이 100개를 넘으면 화면에 페이지 이동을 붙여야 해요.
const MAX_SIZE = 100;

// 주소에 잘못된 값(?sort=abc)이 있어도 422 오류 대신 기본값으로 보여 주도록 걸러요
export async function fetchProducts(query: ProductQuery & { ids?: number[] } = {}): Promise<Page<Product>> {
  if (query.ids && query.ids.length === 0) return { items: [], total: 0, page: 1, size: MAX_SIZE, pages: 0 };

  const params = new URLSearchParams({ size: String(MAX_SIZE) });
  const q = query.q?.trim().slice(0, 50);
  if (q) params.set("q", q);
  if (COUNTRY_FILTERS.some((c) => c.slug === query.country)) params.set("country", query.country!);
  if (query.category) params.set("category", query.category.slice(0, 30));
  if (SORT_OPTIONS.some((o) => o.slug === query.sort)) params.set("sort", query.sort!);
  if (query.ids) params.set("ids", query.ids.slice(0, MAX_SIZE).join(","));

  return api<Page<Product>>(`/products?${params}`);
}

// 없는 상품(또는 숫자가 아닌 주소)이면 undefined → 화면에서 notFound()
export async function fetchProduct(id: number): Promise<Product | undefined> {
  if (!Number.isInteger(id) || id < 1) return undefined;
  try {
    return await api<Product>(`/products/${id}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return undefined;
    throw e;
  }
}

// 카테고리별 상품 수 { snack: 16, … } (GET /categories)
export async function fetchCategoryCounts(): Promise<Record<string, number>> {
  const list = await api<{ slug: string; productCount: number }[]>("/categories");
  return Object.fromEntries(list.map((c) => [c.slug, c.productCount]));
}

// 검색 화면의 추천 검색어
export const POPULAR_KEYWORDS = [
  "도쿄 바나나",
  "펑리수",
  "곤약젤리",
  "초콜릿",
  "코코넛",
  "하리보",
  "마들렌",
  "쌀과자",
];
