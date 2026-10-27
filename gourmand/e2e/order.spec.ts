import { test, expect } from "@playwright/test";

import { fakePostcode } from "./fake-postcode";

// 회원가입 → 카테고리 → 상품 → 장바구니 → 주문 → 마이페이지 주문 내역
// 실제 로컬 DB 에 회원 · 주문이 생겨요 (운영 사이트에는 돌리지 마세요)
test("회원가입부터 주문까지", async ({ page }, testInfo) => {
  // 돌릴 때마다 새 회원. 브라우저 3개가 동시에 돌아서 이름 · 난수도 섞어요 (같은 이메일이면 409)
  const email = `e2e-${testInfo.project.name}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@test.com`;
  const password = "test1234@!~";
  await fakePostcode(page);

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

  // 담으면 '장바구니로 이동할까요?' 창 → 장바구니 → 주문서
  const dialog = page.getByRole("dialog", { name: "장바구니에 담았어요 ✓" });
  await expect(dialog).toContainText(`${productName} · 1개`);
  await expect(page.getByRole("link", { name: "1 장바구니" })).toBeAttached(); // 헤더 숫자도 1
  await dialog.getByRole("button", { name: "장바구니로 이동" }).click();
  await expect(page).toHaveURL("/cart");
  await expect(page.getByText(productName!).first()).toBeVisible();
  await page.getByRole("link", { name: "주문하기" }).click();

  await page.getByRole("textbox", { name: "받는 분" }).fill("김테스트");
  // 숫자만 쳐도 하이픈이 들어가요
  const phone = page.getByRole("textbox", { name: "휴대폰 번호" });
  await phone.pressSequentially("01012345678");
  await expect(phone).toHaveValue("010-1234-5678");

  // 우편번호 · 주소는 [주소 검색]으로만 (직접 칠 수 없어요) → 고르면 상세 주소로 커서
  await expect(page.getByRole("textbox", { name: "우편번호" })).not.toBeEditable();
  await page.getByRole("button", { name: "주소 검색" }).click();
  await page.getByRole("dialog", { name: "주소 검색" }).getByRole("button", { name: "테헤란로 152 선택" }).click();
  await expect(page.getByRole("dialog", { name: "주소 검색" })).toBeHidden();
  await expect(page.getByRole("textbox", { name: "우편번호" })).toHaveValue("06236");
  await expect(page.getByRole("textbox", { name: "주소", exact: true })).toHaveValue("서울 강남구 테헤란로 152 (역삼동)");
  const detail = page.getByRole("textbox", { name: "상세 주소" });
  await expect(detail).toBeFocused();
  await detail.fill("101동 1001호");
  await page.getByRole("checkbox", { name: "이 배송 정보를 내 계정에 저장하고 다음 주문에도 사용하기" }).uncheck();
  await page.getByRole("button", { name: "주문 완료하기" }).click();

  // 주문 완료 → 마이페이지 주문 내역에 '접수'로
  // 주문 API → 완료 화면 이동 → 주문 다시 불러오기라 느린 CI 에서는 5초를 넘기기도 해요
  await expect(page).toHaveURL(/\/order\/complete\?orderId=\d+/, { timeout: 15_000 });
  await expect(page.getByRole("link", { name: "쇼핑 계속하기" })).toBeVisible({ timeout: 15_000 });
  await page.goto("/mypage");
  await expect(page.getByText(productName!).first()).toBeVisible();
  await expect(page.getByText("접수", { exact: true }).filter({ visible: true }).first()).toBeVisible(); // 숨은 필터 <option> 말고
});
