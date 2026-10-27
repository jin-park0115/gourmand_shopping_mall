import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { router } from "./next-mocks";
import SearchField from "@/components/SearchField";

const SUGGEST = {
  total: 9,
  categories: [{ slug: "chocolate", name: "초코·과자", productCount: 12 }],
  countries: [],
  products: [
    { id: 7, name: "초코 파이", imageUrl: "/a.png", price: 3000, salePrice: 2400, isSoldOut: false },
    { id: 8, name: "초코 쿠키", imageUrl: "/b.png", price: 2000, salePrice: 2000, isSoldOut: true },
  ],
};
const EMPTY = { total: 0, categories: [], countries: [], products: [] };

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  router.push.mockClear();
  fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify(SUGGEST)));
  vi.stubGlobal("fetch", fetchMock);
});

const setup = () => {
  render(<SearchField searchPath="/search" className="" placeholder="검색" />);
  return { user: userEvent.setup(), input: screen.getByRole("combobox") };
};

it("치면 제안을 카테고리 · 상품 · 전체 결과 순서로 보여 줘요", async () => {
  const { user, input } = setup();
  await user.type(input, "초코");
  const options = await screen.findAllByRole("option");
  expect(options.map((o) => o.textContent)).toEqual([
    "카테고리초코·과자12개",
    "초코 파이2,400원",
    "초코 쿠키품절",
    "‘초코’ 전체 결과 9개 보기 ›",
  ]);
  expect(input).toHaveAttribute("aria-expanded", "true");
  expect(options[3].querySelector("a")).toHaveAttribute("href", "/search?q=%EC%B4%88%EC%BD%94");
});

it("치기를 멈춘 뒤 한 번만 물어봐요 (글자마다 요청하지 않아요)", async () => {
  const { user, input } = setup();
  await user.type(input, "초코파이");
  await screen.findAllByRole("option");
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(new URL(fetchMock.mock.calls[0][0]).searchParams.get("q")).toBe("초코파이");
});

it("검색어와 같은 글자는 굵게", async () => {
  const { user, input } = setup();
  await user.type(input, "파이");
  await screen.findAllByRole("option");
  expect(screen.getByText("파이", { selector: "strong" })).toBeInTheDocument();
});

it("↓ 로 고르고 Enter → 그 제안으로 이동", async () => {
  const { user, input } = setup();
  await user.type(input, "초코");
  await screen.findAllByRole("option");
  await user.keyboard("{ArrowDown}{ArrowDown}");
  expect(screen.getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");
  expect(input.getAttribute("aria-activedescendant")).toBe(screen.getAllByRole("option")[1].id);
  await user.keyboard("{Enter}");
  expect(router.push).toHaveBeenCalledWith("/products/7");
});

it("↑ 는 맨 아래부터, 끝에서 더 가면 검색창으로 돌아와요", async () => {
  const { user, input } = setup();
  await user.type(input, "초코");
  await screen.findAllByRole("option");
  await user.keyboard("{ArrowUp}");
  expect(screen.getAllByRole("option")[3]).toHaveAttribute("aria-selected", "true");
  await user.keyboard("{ArrowDown}");
  expect(input).not.toHaveAttribute("aria-activedescendant");
});

it("고른 게 없으면 Enter 로 이동하지 않아요 (원래 검색으로)", async () => {
  const { user, input } = setup();
  await user.type(input, "초코");
  await screen.findAllByRole("option");
  await user.keyboard("{Enter}");
  expect(router.push).not.toHaveBeenCalled();
});

it("Esc 는 목록만 닫고 친 글자는 남겨요", async () => {
  const { user, input } = setup();
  await user.type(input, "초코");
  await screen.findAllByRole("option");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  expect(input).toHaveValue("초코");
});

it("맞는 게 없으면 안내 문구", async () => {
  fetchMock.mockImplementation(async () => new Response(JSON.stringify(EMPTY)));
  const { user, input } = setup();
  await user.type(input, "zzz");
  expect(await screen.findByText("‘zzz’에 맞는 간식이 아직 없어요.")).toBeInTheDocument();
});

it("서버가 실패하면 조용히 안 보여 줘요 (검색은 계속 가능)", async () => {
  fetchMock.mockImplementation(async () => new Response("", { status: 500 }));
  const { user, input } = setup();
  await user.type(input, "초코");
  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
});

it("더 쳤으면 이전 요청은 취소하고, 늦게 온 옛 결과는 안 보여 줘요", async () => {
  let resolveOld!: (r: Response) => void;
  const signals: AbortSignal[] = [];
  fetchMock.mockImplementationOnce((_url: string, init: RequestInit) => {
    signals.push(init.signal!);
    return new Promise<Response>((r) => (resolveOld = r));
  });
  const { user, input } = setup();
  await user.type(input, "초");
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  await user.type(input, "코");
  expect(signals[0].aborted).toBe(true);
  resolveOld(new Response(JSON.stringify(EMPTY))); // 옛 결과가 늦게 도착
  expect(await screen.findByText("‘초코’ 전체 결과 9개 보기 ›")).toBeInTheDocument();
});

it("목록을 누르는 순간 검색창 포커스가 빠지지 않아요 (Safari 클릭 버그)", async () => {
  const { user, input } = setup();
  await user.type(input, "초코");
  const listbox = await screen.findByRole("listbox");
  expect(fireEvent.mouseDown(listbox)).toBe(false); // preventDefault 됨
});

it("다른 곳으로 포커스가 가면 닫혀요", async () => {
  const { user, input } = setup();
  await user.type(input, "초코");
  await screen.findAllByRole("option");
  fireEvent.blur(input, { relatedTarget: document.body });
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
});
