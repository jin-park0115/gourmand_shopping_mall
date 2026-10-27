import { expect, it } from "vitest";

// 머지 막힘 확인용 (이 PR은 머지하지 않고 닫아요)
it("일부러 실패", () => {
  expect(1).toBe(2);
});
