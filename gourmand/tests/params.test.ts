import { expect, it } from "vitest";

import { firstParams } from "@/lib/params";

it("같은 이름이 여러 번 오면 첫 번째 값만 (?q=a&q=b)", () => {
  expect(firstParams({ q: ["a", "b"], sort: "low" }, "q", "sort")).toEqual({ q: "a", sort: "low" });
});

it("없는 값은 빼고, 빈 글자는 그대로 둬요", () => {
  expect(firstParams({ q: "", country: undefined }, "q", "country", "sort")).toEqual({ q: "" });
});

it("빈 배열이면 없는 값", () => {
  expect(firstParams({ q: [] }, "q")).toEqual({});
});
