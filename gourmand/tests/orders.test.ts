import { expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import { shippingErrorField } from "@/lib/orders";

// 서버 배송 정보 검증 문구 → 어느 입력칸 아래에 보여 줄지
it.each([
  ["받는 분 이름을 입력해 주세요.", "buyerName"],
  ["휴대폰 번호를 올바르게 입력해 주세요. (예: 010-1234-5678)", "phone"],
  ["우편번호 5자리를 입력해 주세요.", "zipcode"],
  ["주소를 입력해 주세요.", "address1"],
  ["알 수 없는 문구", null],
])("%s → %s", (message, field) => {
  expect(shippingErrorField(new ApiError(422, "INVALID_VALUE", message))).toBe(field);
});

it("배송 정보 오류가 아니면(409 · 일반 Error) 칸을 찾지 않아요", () => {
  expect(shippingErrorField(new ApiError(409, "BUSINESS_RULE_VIOLATION", "주소가 바뀌었어요"))).toBeNull();
  expect(shippingErrorField(new Error("받는 분"))).toBeNull();
});
