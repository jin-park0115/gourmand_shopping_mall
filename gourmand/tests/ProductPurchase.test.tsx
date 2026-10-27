import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { router } from "./next-mocks";
import ProductPurchase from "@/components/ProductPurchase";
import { ApiError } from "@/lib/api";
import type { Product } from "@/types/product";

const addItem = vi.fn();
let cartItems: { id: number; quantity: number }[] = [];
vi.mock("@/components/CartProvider", () => ({
  useCart: () => ({ addItem, items: cartItems }),
  cartErrorMessage: (e: Error) => e.message,
}));

const product = { id: 7, name: "초코 파이", stock: 10 } as Product;

beforeEach(() => {
  router.push.mockClear();
  addItem.mockReset();
  cartItems = [];
});

const setup = () => {
  render(<ProductPurchase p={product} price={2400} soldOut={false} />);
  return userEvent.setup();
};

it("담으면 '장바구니로 이동할까요?' 창이 떠요 (담은 수량과 함께)", async () => {
  addItem.mockResolvedValue(true);
  const user = setup();
  await user.click(screen.getByRole("button", { name: "수량 늘리기" }));
  await user.click(screen.getByRole("button", { name: "장바구니 담기" }));
  expect(addItem).toHaveBeenCalledWith(7, 2);
  const dialog = screen.getByRole("dialog", { name: "장바구니에 담았어요 ✓" });
  expect(dialog).toHaveTextContent("초코 파이 · 2개");
  expect(screen.getByText("1")).toBeInTheDocument(); // 수량은 1로 돌아가요
});

it("이미 담긴 상품이면 수량을 더했다고 · 총 몇 개인지 알려 줘요", async () => {
  cartItems = [{ id: 7, quantity: 3 }];
  addItem.mockResolvedValue(true);
  const user = setup();
  await user.click(screen.getByRole("button", { name: "수량 늘리기" }));
  await user.click(screen.getByRole("button", { name: "장바구니 담기" }));
  const dialog = screen.getByRole("dialog", { name: "이미 담긴 상품이라 수량을 더했어요 ✓" });
  expect(dialog).toHaveTextContent("초코 파이 · 2개 추가");
  expect(dialog).toHaveTextContent("장바구니에 총 5개");
});

it("장바구니로 이동 → /cart", async () => {
  addItem.mockResolvedValue(true);
  const user = setup();
  await user.click(screen.getByRole("button", { name: "장바구니 담기" }));
  await user.click(screen.getByRole("button", { name: "장바구니로 이동" }));
  expect(router.push).toHaveBeenCalledWith("/cart");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("쇼핑 계속하기 → 창만 닫고 그대로", async () => {
  addItem.mockResolvedValue(true);
  const user = setup();
  await user.click(screen.getByRole("button", { name: "장바구니 담기" }));
  await user.click(screen.getByRole("button", { name: "쇼핑 계속하기" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(router.push).not.toHaveBeenCalled();
});

it("로그인 안내로 끝났거나(false) 실패하면 창을 띄우지 않아요", async () => {
  addItem.mockResolvedValueOnce(false).mockRejectedValueOnce(new ApiError(409, "BUSINESS_RULE_VIOLATION", "재고가 부족해요."));
  const user = setup();
  await user.click(screen.getByRole("button", { name: "장바구니 담기" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "장바구니 담기" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByText("재고가 부족해요.")).toBeInTheDocument();
});
