import { api, type Page } from "@/lib/api";

// 리뷰 API (SCRUM-25). 로그인 토큰은 api() 가 붙여 줘요
export interface Review {
  id: number;
  productId: number;
  authorName: string;
  rating: number; // 1~5
  content: string; // 10~1000자
  createdAt: string; // "2026-10-26T14:03:00+09:00" (KST)
  updatedAt: string | null; // 수정한 적 없으면 null
  isMine: boolean;
}

export type ReviewInput = { rating: number; content: string };

export const CONTENT_MIN = 10;
export const CONTENT_MAX = 1000;
export const PAGE_SIZE = 10;

// 공개 목록이라 토큰이 만료돼도 로그인 화면으로 보내지 않아요 (그때는 isMine 만 false)
export const fetchReviews = (productId: number, page: number) =>
  api<Page<Review>>(`/products/${productId}/reviews?page=${page}&size=${PAGE_SIZE}`, undefined, {
    redirectOn401: false,
  });

// 리뷰는 배송완료된 주문으로 받은 상품만 쓸 수 있어요. 못 쓰면 message 에 이유가 와요 (로그인 필요)
export const fetchReviewWritable = (productId: number) =>
  api<{ canWrite: boolean; message: string | null }>(`/products/${productId}/reviews/writable`, undefined, {
    redirectOn401: false,
  });

const json = (method: string, body: ReviewInput) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const createReview = (productId: number, body: ReviewInput) =>
  api<Review>(`/products/${productId}/reviews`, json("POST", body));

export const updateReview = (reviewId: number, body: ReviewInput) =>
  api<Review>(`/reviews/${reviewId}`, json("PATCH", body));

export const deleteReview = (reviewId: number) => api<void>(`/reviews/${reviewId}`, { method: "DELETE" });

// "2026-10-26T14:03:00+09:00" → "2026.10.26" (서버가 KST 로 줘서 앞 10자리가 한국 날짜예요)
export const reviewDate = (iso: string) => iso.slice(0, 10).replaceAll("-", ".");
