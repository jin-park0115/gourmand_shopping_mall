import { beforeEach, describe, expect, it, vi } from "vitest";

import { discountRate, fetchProduct, fetchProducts, hasDiscount, isSoldOut, salePrice } from "@/lib/products";

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchMock = vi.fn().mockResolvedValue(json(200, { items: [], total: 0, page: 1, size: 100, pages: 0 }));
  vi.stubGlobal("fetch", fetchMock);
});

const sentParams = () => new URL(fetchMock.mock.calls[0][0]).searchParams;

describe("가격 · 품절", () => {
  it.each([
    [{ price: 3000, discountPrice: null }, false, 3000, 0], // null < 3000 이 true 라서 생길 뻔한 버그
    [{ price: 3000, discountPrice: 2400 }, true, 2400, 20],
    [{ price: 3000, discountPrice: 3000 }, false, 3000, 0], // 같으면 할인 아님
    [{ price: 3000, discountPrice: 3500 }, false, 3000, 0], // 더 비싸면 할인 아님
    [{ price: 3000, discountPrice: 0 }, true, 0, 100],
  ])("%o → 할인 %s, 판매가 %i, %i%%", (p, discounted, sale, rate) => {
    expect(hasDiscount(p)).toBe(discounted);
    expect(salePrice(p)).toBe(sale);
    expect(discountRate(p)).toBe(rate);
  });

  it.each([
    [{ isSoldOut: true, stock: 10 }, true],
    [{ isSoldOut: false, stock: 0 }, true],
    [{ isSoldOut: false, stock: 1 }, false],
  ])("%o → 품절 %s", (p, expected) => {
    expect(isSoldOut(p)).toBe(expected);
  });
});

describe("fetchProduct: 상세", () => {
  it.each([0, -1, 1.5, NaN, 2_147_483_648, 99_999_999_999])("%s 번은 서버에 묻지 않고 '없는 상품'", async (id) => {
    expect(await fetchProduct(id)).toBeUndefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("404 → '없는 상품'", async () => {
    fetchMock.mockResolvedValue(json(404, { code: "NOT_FOUND", message: "없어요" }));
    expect(await fetchProduct(2_147_483_647)).toBeUndefined();
  });

  it("그 밖의 오류(500)는 그대로 던져서 오류 화면", async () => {
    fetchMock.mockResolvedValue(json(500, { code: "INTERNAL_ERROR", message: "잠시 후" }));
    await expect(fetchProduct(1)).rejects.toMatchObject({ status: 500 });
  });
});

describe("fetchProducts: 목록 주소 만들기", () => {
  it("잘못된 정렬 · 나라는 빼고 보내요 (422 대신 기본값)", async () => {
    await fetchProducts({ sort: "abc", country: "korea", q: "  초코  " });
    const p = sentParams();
    expect(p.has("sort")).toBe(false);
    expect(p.has("country")).toBe(false);
    expect(p.get("q")).toBe("초코");
  });

  it("맞는 값은 그대로, 검색어는 50자까지", async () => {
    await fetchProducts({ sort: "low", country: "japan", category: "jelly", q: "가".repeat(80) });
    const p = sentParams();
    expect(p.get("sort")).toBe("low");
    expect(p.get("country")).toBe("japan");
    expect(p.get("category")).toBe("jelly");
    expect(p.get("q")).toHaveLength(50);
  });

  it("빈 검색어는 안 보내요", async () => {
    await fetchProducts({ q: "   " });
    expect(sentParams().has("q")).toBe(false);
  });

  it("최근 본 상품이 없으면(ids 빈 배열) 묻지 않고 빈 목록", async () => {
    expect((await fetchProducts({ ids: [] })).items).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("ids 는 100개까지 쉼표로", async () => {
    await fetchProducts({ ids: Array.from({ length: 120 }, (_, i) => i + 1) });
    expect(sentParams().get("ids")!.split(",")).toHaveLength(100);
  });
});
