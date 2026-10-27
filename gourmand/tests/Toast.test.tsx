import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider, useToast } from "@/components/Toast";

function Buttons() {
  const toast = useToast();
  let n = 0;
  return (
    <>
      <button onClick={() => toast(`완료 ${++n}`)}>성공</button>
      <button onClick={() => toast("재고가 부족해요.", "error")}>실패</button>
    </>
  );
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

const renderToasts = () =>
  render(
    <ToastProvider>
      <Buttons />
    </ToastProvider>
  );

it("성공은 status, 오류는 alert 로 (화면 낭독기가 오류는 바로 읽어요)", () => {
  renderToasts();
  fireEvent.click(screen.getByText("성공"));
  fireEvent.click(screen.getByText("실패"));
  expect(screen.getByRole("status")).toHaveTextContent("완료 1");
  expect(screen.getByRole("alert")).toHaveTextContent("재고가 부족해요.");
});

it("3초 뒤 사라져요", () => {
  renderToasts();
  fireEvent.click(screen.getByText("실패"));
  act(() => vi.advanceTimersByTime(2999));
  expect(screen.queryByRole("alert")).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(1));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("한 번에 최대 3개 (오래된 것부터 빠져요)", () => {
  renderToasts();
  for (let i = 0; i < 5; i++) fireEvent.click(screen.getByText("성공"));
  expect(screen.getAllByRole("status").map((t) => t.textContent)).toEqual(["완료 3", "완료 4", "완료 5"]);
});

it("ToastProvider 밖에서 쓰면 바로 알려 줘요", () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  expect(() => render(<Buttons />)).toThrow("ToastProvider 안에서만");
});
