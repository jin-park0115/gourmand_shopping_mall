import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, API_URL, getToken, loginHref, setToken } from "@/lib/api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

let fetchMock: ReturnType<typeof vi.fn>;
let assign: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  assign = vi.fn(); // jsdom 은 실제 이동을 못 해서, 어디로 보내려 했는지만 봐요
  vi.stubGlobal("location", { pathname: "/cart", search: "?x=1", assign });
});

describe("api(): 요청", () => {
  it("API 주소를 붙이고, 로그인했으면 토큰을 실어 보내요", async () => {
    setToken("tok");
    fetchMock.mockResolvedValue(json(200, { ok: 1 }));
    expect(await api("/cart")).toEqual({ ok: 1 });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_URL}/cart`);
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer tok");
  });

  it("로그인 안 했으면 Authorization 이 없어요", async () => {
    fetchMock.mockResolvedValue(json(200, []));
    await api("/products");
    expect(new Headers(fetchMock.mock.calls[0][1].headers).has("Authorization")).toBe(false);
  });

  it("204 는 undefined", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    expect(await api("/reviews/1", { method: "DELETE" })).toBeUndefined();
  });
});

describe("api(): 오류 → ApiError", () => {
  it.each([
    [404, "NOT_FOUND", "상품을 찾을 수 없어요."],
    [409, "BUSINESS_RULE_VIOLATION", "재고가 부족해요."],
    [422, "VALIDATION_ERROR", "rating: 5 이하로 입력해 주세요."],
    [429, "TOO_MANY_REQUESTS", "10분 뒤에 다시 시도해 주세요."],
  ])("%i → 서버의 code · message 그대로", async (status, code, message) => {
    fetchMock.mockResolvedValue(json(status, { code, message }));
    const err = await api("/x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status, code, message });
  });

  it("본문이 JSON 이 아니면(프록시 502 등) 기본 문구", async () => {
    fetchMock.mockResolvedValue(new Response("<html>Bad Gateway</html>", { status: 502 }));
    await expect(api("/x")).rejects.toMatchObject({ status: 502, code: "HTTP_ERROR", message: "요청에 실패했어요. (502)" });
  });

  it("서버에 연결이 안 되면 fetch 오류가 그대로 (화면은 '연결할 수 없어요')", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(api("/x")).rejects.toBeInstanceOf(TypeError);
  });
});

describe("api(): 401", () => {
  const unauthorized = () => json(401, { code: "UNAUTHORIZED", message: "로그인이 만료됐어요." });

  it("토큰이 만료됐으면 지우고 로그인 화면으로 (보던 주소를 next 로)", async () => {
    setToken("old");
    fetchMock.mockResolvedValue(unauthorized());
    await expect(api("/cart")).rejects.toMatchObject({ status: 401 });
    expect(getToken()).toBeNull();
    expect(assign).toHaveBeenCalledWith("/login?next=%2Fcart%3Fx%3D1");
  });

  it("redirectOn401: false 면 토큰만 지우고 이동은 안 해요 (헤더의 로그인 확인)", async () => {
    setToken("old");
    fetchMock.mockResolvedValue(unauthorized());
    await expect(api("/auth/me", undefined, { redirectOn401: false })).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBeNull();
    expect(assign).not.toHaveBeenCalled();
  });

  it("토큰 없이 401(비밀번호 틀림)은 이동 안 해요", async () => {
    fetchMock.mockResolvedValue(unauthorized());
    await expect(api("/auth/login")).rejects.toBeInstanceOf(ApiError);
    expect(assign).not.toHaveBeenCalled();
  });

  it("이미 로그인 화면이면 다시 보내지 않아요", async () => {
    vi.stubGlobal("location", { pathname: "/login", search: "", assign });
    setToken("old");
    fetchMock.mockResolvedValue(unauthorized());
    await expect(api("/auth/me")).rejects.toBeInstanceOf(ApiError);
    expect(assign).not.toHaveBeenCalled();
  });
});

describe("토큰 · 로그인 주소", () => {
  it("setToken 은 저장 · 삭제하고 화면에 알려요", () => {
    const changed = vi.fn();
    window.addEventListener("gourmand-auth-changed", changed);
    setToken("a");
    expect(getToken()).toBe("a");
    setToken(null);
    expect(getToken()).toBeNull();
    expect(changed).toHaveBeenCalledTimes(2);
    window.removeEventListener("gourmand-auth-changed", changed);
  });

  it("저장소를 못 쓰는 브라우저(사생활 보호 모드 등)여도 오류 없이 null", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    expect(getToken()).toBeNull();
  });

  it.each([
    [undefined, "/login"],
    ["/", "/login"],
    ["/cart", "/login?next=%2Fcart"],
  ])("loginHref(%s) → %s", (next, expected) => {
    expect(loginHref(next)).toBe(expected);
  });
});
