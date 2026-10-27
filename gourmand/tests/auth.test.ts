import { describe, expect, it } from "vitest";

import { afterLoginPath, safeNext } from "@/lib/auth";

describe("safeNext: 로그인 후 돌아갈 주소는 우리 사이트 안만", () => {
  it.each([
    ["/cart", "/cart"],
    ["/products/7?tab=review#top", "/products/7?tab=review#top"],
    ["/search?q=%EC%B4%88%EC%BD%94", "/search?q=%EC%B4%88%EC%BD%94"],
  ])("%s → 그대로", (next, expected) => {
    expect(safeNext(next)).toBe(expected);
  });

  it.each([
    null,
    "",
    "cart", // / 로 시작하지 않음
    "https://evil.com",
    "//evil.com",
    "/\\evil.com", // 브라우저는 \ 를 / 로 읽어요
    "/\\/evil.com",
    "javascript:alert(1)",
  ])("%s → 홈", (next) => {
    expect(safeNext(next)).toBe("/");
  });
});

describe("afterLoginPath: 역할별로 갈 곳", () => {
  it.each([
    ["admin", "/", "/admin"],
    ["admin", "/cart", "/admin"],
    ["admin", "/admin/orders/3", "/admin/orders/3"],
    ["admin", "/admin?status=접수", "/admin?status=접수"],
    ["customer", "/cart", "/cart"],
    ["customer", "/admin", "/"],
    ["customer", "/admin/orders", "/"],
    ["customer", "/administrator", "/administrator"], // /admin 으로 시작만 하는 다른 주소는 막지 않아요
  ] as const)("%s, next=%s → %s", (role, next, expected) => {
    expect(afterLoginPath(role, next)).toBe(expected);
  });
});
