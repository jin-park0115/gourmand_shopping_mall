"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/AuthProvider";
import { ApiError, loginHref } from "@/lib/api";
import {
  CONTENT_MAX,
  CONTENT_MIN,
  createReview,
  deleteReview,
  fetchReviews,
  reviewDate,
  updateReview,
  type Review,
  type ReviewInput,
} from "@/lib/reviews";

const errorText = (e: unknown) =>
  e instanceof ApiError ? e.message : "서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.";

function Stars({ rating }: { rating: number }) {
  return (
    <span aria-label={`별점 ${rating}점`} className="tracking-tight">
      <span className="text-[#f5a623]">{"★".repeat(rating)}</span>
      <span className="text-gray-300">{"★".repeat(5 - rating)}</span>
    </span>
  );
}

// 작성 · 수정 폼 (별점 고르기 + 내용)
function ReviewForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial?: ReviewInput;
  submitLabel: string;
  onSubmit: (body: ReviewInput) => Promise<void>;
  onCancel?: () => void;
}) {
  const [rating, setRating] = useState(initial?.rating ?? 0);
  const [content, setContent] = useState(initial?.content ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const length = content.trim().length;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating === 0) return setError("별점을 골라 주세요.");
    if (length < CONTENT_MIN || length > CONTENT_MAX)
      return setError(`리뷰는 ${CONTENT_MIN}~${CONTENT_MAX}자로 써 주세요.`);
    setError(null);
    setPending(true);
    try {
      await onSubmit({ rating, content: content.trim() });
    } catch (err) {
      setError(errorText(err));
      setPending(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3 rounded-xl border border-gray-200 bg-gray-50 p-4">
      <fieldset className="flex items-center gap-1">
        <legend className="sr-only">별점</legend>
        {[1, 2, 3, 4, 5].map((n) => (
          <label key={n} className="cursor-pointer text-2xl leading-none">
            <input
              type="radio"
              name="rating"
              value={n}
              checked={rating === n}
              onChange={() => setRating(n)}
              className="sr-only"
            />
            <span className={n <= rating ? "text-[#f5a623]" : "text-gray-300"}>★</span>
            <span className="sr-only">{n}점</span>
          </label>
        ))}
        <span className="ml-2 text-sm text-gray-500">{rating ? `${rating}점` : "별점을 골라 주세요"}</span>
      </fieldset>

      <label className="block">
        <span className="sr-only">리뷰 내용</span>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          maxLength={CONTENT_MAX}
          rows={4}
          placeholder={`맛, 식감, 포장 상태를 ${CONTENT_MIN}자 이상 알려 주세요.`}
          className="w-full resize-y rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand"
        />
      </label>

      <div className="flex items-center justify-between gap-2">
        <span className={`text-xs ${length < CONTENT_MIN ? "text-gray-400" : "text-gray-600"}`}>
          {length} / {CONTENT_MAX}자
        </span>
        <div className="flex gap-2">
          {onCancel && (
            <button type="button" onClick={onCancel} className="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100">
              취소
            </button>
          )}
          <button
            type="submit"
            disabled={pending}
            className="rounded-lg bg-brand px-5 py-2 text-sm font-semibold text-white hover:bg-brand-dark disabled:opacity-60"
          >
            {pending ? "저장 중…" : submitLabel}
          </button>
        </div>
      </div>

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}
    </form>
  );
}

// 상품 상세의 리뷰 칸: 작성 폼 + 목록(최신순, 10개씩 더보기) + 내 리뷰 수정 · 삭제
export default function ProductReviews({ productId }: { productId: number }) {
  const router = useRouter();
  const { member, ready } = useAuth();
  const [items, setItems] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  // page 1 이면 새로, 아니면 뒤에 이어 붙여요
  const load = useCallback(
    (nextPage: number) =>
      fetchReviews(productId, nextPage).then(
        (res) => {
          setItems((prev) => (nextPage === 1 ? res.items : [...prev, ...res.items]));
          setTotal(res.total);
          setPage(res.page);
          setPages(res.pages);
          setError(null);
          setLoaded(true);
        },
        (e) => {
          setError(errorText(e));
          setLoaded(true);
        }
      ),
    [productId]
  );

  // 로그인 확인이 끝난 뒤 불러와야 내 리뷰(isMine)가 맞게 나와요. 로그인 · 로그아웃하면 다시 불러요
  useEffect(() => {
    if (ready) load(1);
  }, [ready, member?.id, load]);

  // 작성 · 수정 · 삭제 후: 목록을 처음부터 다시, 위쪽 평균 별점 · 리뷰 수는 서버 화면을 새로 그려서
  const afterChange = async () => {
    setEditingId(null);
    await load(1);
    router.refresh();
  };

  const remove = async (id: number) => {
    if (!confirm("리뷰를 삭제할까요? 삭제하면 되돌릴 수 없어요.")) return;
    try {
      await deleteReview(id);
      await afterChange();
    } catch (e) {
      alert(errorText(e));
    }
  };

  // ponytail: 불러온 페이지 안에서만 내 리뷰를 찾아요. 더 뒤에 있으면 등록할 때 서버가 409 로 알려 줘요
  const wroteAlready = items.some((r) => r.isMine);

  return (
    <section id="reviews" className="mt-14 scroll-mt-24">
      <h2 className="text-xl font-bold text-gray-900">
        리뷰 <span className="text-brand">{total.toLocaleString()}</span>개
      </h2>

      <div className="mt-4">
        {!ready ? null : !member ? (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm">
            <span className="text-gray-600">구매한 간식은 어땠나요? 로그인하면 리뷰를 쓸 수 있어요.</span>
            <Link
              href={loginHref(`/products/${productId}`)}
              className="shrink-0 rounded-lg bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark"
            >
              로그인하고 리뷰 쓰기
            </Link>
          </div>
        ) : wroteAlready ? (
          <p className="rounded-xl bg-brand-soft px-4 py-3 text-sm text-brand">
            이 상품에 리뷰를 작성했어요. 아래에서 수정하거나 삭제할 수 있어요.
          </p>
        ) : (
          <ReviewForm
            key={total} // 등록 · 삭제 뒤 폼을 비워요
            submitLabel="리뷰 등록"
            onSubmit={async (body) => {
              await createReview(productId, body);
              await afterChange();
            }}
          />
        )}
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      {loaded && !error && items.length === 0 && (
        <p className="mt-6 py-8 text-center text-sm text-gray-500">아직 리뷰가 없어요. 첫 리뷰를 남겨 주세요!</p>
      )}

      <ul className="mt-4 divide-y divide-gray-200 border-t border-gray-200">
        {items.map((r) => (
          <li key={r.id} className="py-5">
            {editingId === r.id ? (
              <ReviewForm
                initial={{ rating: r.rating, content: r.content }}
                submitLabel="수정 완료"
                onCancel={() => setEditingId(null)}
                onSubmit={async (body) => {
                  await updateReview(r.id, body);
                  await afterChange();
                }}
              />
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                  <strong className="font-semibold text-gray-900">{r.authorName}</strong>
                  {r.isMine && <span className="rounded bg-brand-soft px-1.5 py-0.5 text-xs font-semibold text-brand">내 리뷰</span>}
                  <Stars rating={r.rating} />
                  <span className="text-gray-400">
                    {reviewDate(r.createdAt)}
                    {r.updatedAt && " (수정됨)"}
                  </span>
                  {r.isMine && (
                    <span className="ml-auto flex gap-1">
                      <button type="button" onClick={() => setEditingId(r.id)} className="rounded px-2 py-1 text-gray-600 hover:bg-gray-100">
                        수정
                      </button>
                      <button type="button" onClick={() => remove(r.id)} className="rounded px-2 py-1 text-red-500 hover:bg-red-50">
                        삭제
                      </button>
                    </span>
                  )}
                </div>
                <p className="mt-2 whitespace-pre-line text-[15px] leading-relaxed text-gray-700">{r.content}</p>
              </>
            )}
          </li>
        ))}
      </ul>

      {page < pages && (
        <button
          type="button"
          onClick={() => load(page + 1)}
          className="mt-4 w-full rounded-xl border border-gray-300 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50"
        >
          리뷰 더보기 ({items.length} / {total})
        </button>
      )}
    </section>
  );
}
