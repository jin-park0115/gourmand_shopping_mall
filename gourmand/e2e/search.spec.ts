import { test, expect } from "@playwright/test";

test("검색 화면 → 자동완성 → 상세", async ({ page }) => {
  await page.goto("/search", { waitUntil: "networkidle" }); // React 가 붙기 전에 치면 입력이 무시돼요
  const box = page.locator('input[role="combobox"]:visible').last();
  const option = page.getByRole("option").filter({ hasText: "원" }).first();
  // 컴퓨터가 바쁘면 networkidle 뒤에도 React 가 늦게 붙어서 입력이 무시될 수 있어요. 목록이 뜰 때까지 다시 쳐요
  await expect(async () => {
    await box.fill("");
    await box.fill("ㅊㅋ");
    await expect(option).toBeVisible({ timeout: 2000 });
  }).toPass({ timeout: 15_000 });
  await option.click();
  await expect(page).toHaveURL(/\/products\/\d+$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});
