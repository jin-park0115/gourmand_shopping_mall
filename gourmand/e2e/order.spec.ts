import { test, expect } from "@playwright/test";

// 회원가입 → 카테고리 → 상품 → 장바구니 → 주문 → 마이페이지 주문 내역
// 실제 로컬 DB 에 회원 · 주문이 생겨요 (운영 사이트에는 돌리지 마세요)
test("회원가입부터 주문까지", async ({ page }, testInfo) => {
  // 돌릴 때마다 새 회원. 브라우저 3개가 동시에 돌아서 이름 · 난수도 섞어요 (같은 이메일이면 409)
  const email = `e2e-${testInfo.project.name}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@test.com`;
  const password = "test1234@!~";

  // 회원가입 (끝나면 바로 로그인돼서 홈으로)
  await page.goto("/signup", { waitUntil: "networkidle" });
  await page.getByRole("textbox", { name: "이메일" }).fill(email);
  // 레이블에 '보기' 버튼 글자가 섞여서 name 으로. 스트리밍 중엔 숨은 복사본이 잠깐 있어서 보이는 것만
  await page.locator('input[name="password"]:visible').fill(password);
  await page.getByRole("textbox", { name: "비밀번호 확인" }).fill(password);
  await expect(page.getByText("비밀번호가 같아요 ✓")).toBeVisible();
  await page.getByRole("textbox", { name: "이름" }).fill("김테스트");
  await page.getByRole("button", { name: "가입하고 로그인" }).click();
  await expect(page).toHaveURL("/");

  // 카테고리 → 상품 → 장바구니 담기
  await page.getByRole("link", { name: /^젤리·캔디/ }).click();
  await page.locator("a").filter({ hasText: "프랑스" }).first().click();
  await expect(page).toHaveURL(/\/products\/\d+$/);
  const productName = await page.getByRole("heading", { level: 1 }).textContent();
  await page.getByRole("button", { name: "장바구니 담기", exact: true }).click();

  // 장바구니 → 주문서
  await page.getByRole("link", { name: "1 장바구니" }).click();
  await expect(page.getByText(productName!).first()).toBeVisible();
  await page.getByRole("link", { name: "주문하기" }).click();

  await page.getByRole("textbox", { name: "받는 분" }).fill("김테스트");
  await page.getByRole("textbox", { name: "휴대폰 번호" }).fill("01012345678");
  await page.getByRole("textbox", { name: "우편번호" }).fill("12345");
  await page.getByRole("textbox", { name: "주소", exact: true }).fill("구로101");
  await page.getByRole("checkbox", { name: "이 배송 정보를 내 계정에 저장하고 다음 주문에도 사용하기" }).uncheck();
  await page.getByRole("button", { name: "주문 완료하기" }).click();

  // 주문 완료 → 마이페이지 주문 내역에 '접수'로
  await expect(page.getByRole("link", { name: "쇼핑 계속하기" })).toBeVisible();
  await page.goto("/mypage");
  await expect(page.getByText(productName!).first()).toBeVisible();
  await expect(page.getByText("접수", { exact: true }).filter({ visible: true }).first()).toBeVisible(); // 숨은 필터 <option> 말고
});
