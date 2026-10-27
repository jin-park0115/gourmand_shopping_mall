import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "./next-mocks";
import { formatAddress } from "@/components/AddressSearch";
import CheckoutForm from "@/components/CheckoutForm";

vi.mock("@/components/AuthProvider", () => ({ useAuth: () => ({ member: { id: 1 } }) }));
vi.mock("@/components/CartProvider", () => ({
  useCart: () => ({
    items: [{ id: 7, name: "초코 파이", price: 2400, quantity: 1 }],
    hydrated: true,
    totalCount: 1,
    totalPrice: 2400,
    orderable: true,
    reload: () => {},
  }),
  cartErrorMessage: (e: Error) => e.message,
}));
vi.mock("@/lib/orders", () => ({
  fetchSavedAddress: () => Promise.resolve(null),
  placeOrder: vi.fn(),
  shippingErrorField: () => null,
}));

const base = { zonecode: "06236", roadAddress: "서울 강남구 테헤란로 152", jibunAddress: "서울 강남구 역삼동 737" };

describe("formatAddress: 도로명 주소 + (동, 아파트 이름)", () => {
  it.each([
    [{ bname: "역삼동", buildingName: "강남파이낸스센터", apartment: "N" }, "서울 강남구 테헤란로 152 (역삼동)"],
    [{ bname: "역삼동", buildingName: "역삼래미안", apartment: "Y" }, "서울 강남구 테헤란로 152 (역삼동, 역삼래미안)"],
    [{ bname: "", buildingName: "", apartment: "N" }, "서울 강남구 테헤란로 152"],
    [{ bname: "율량리", buildingName: "", apartment: "N" }, "서울 강남구 테헤란로 152"], // 리는 붙이지 않아요
  ] as const)("%o → %s", (extra, expected) => {
    expect(formatAddress({ ...base, userSelectedType: "R", ...extra })).toBe(expected);
  });

  it("지번을 골랐으면 지번 주소 그대로", () => {
    expect(formatAddress({ ...base, userSelectedType: "J", bname: "역삼동", buildingName: "", apartment: "N" })).toBe(
      "서울 강남구 역삼동 737"
    );
  });
});

describe("주문서 배송 정보", () => {
  beforeEach(() => {
    // 카카오 스크립트 대신: 창 안에 '선택' 버튼을 그리고 누르면 결과를 돌려줘요
    window.daum = {
      Postcode: class {
        constructor(private o: { oncomplete: (d: Parameters<typeof formatAddress>[0]) => void }) {}
        embed(el: HTMLElement) {
          const b = document.createElement("button");
          b.type = "button";
          b.textContent = "선택";
          b.onclick = () => this.o.oncomplete({ ...base, userSelectedType: "R", bname: "역삼동", buildingName: "", apartment: "N" });
          el.appendChild(b);
        }
      },
    };
  });
  afterEach(() => {
    delete window.daum;
  });

  const field = (name: string) => document.querySelector<HTMLInputElement>(`[name="${name}"]`)!;

  it("휴대폰 번호는 숫자만 쳐도 하이픈이 들어가요", async () => {
    const user = userEvent.setup();
    render(<CheckoutForm />);
    await user.type(field("phone"), "01012345678");
    expect(field("phone")).toHaveValue("010-1234-5678");
  });

  it("우편번호 · 주소는 직접 못 쓰고, 주소 검색으로 채운 뒤 상세 주소로 커서", async () => {
    const user = userEvent.setup();
    render(<CheckoutForm />);
    expect(field("zipcode")).toHaveAttribute("readonly");
    expect(field("address1")).toHaveAttribute("readonly");

    await user.click(field("address1")); // 칸을 눌러도 검색 창이 열려요
    await user.click(await screen.findByRole("button", { name: "선택" }));
    expect(field("zipcode")).toHaveValue("06236");
    expect(field("address1")).toHaveValue("서울 강남구 테헤란로 152 (역삼동)");
    await waitFor(() => expect(field("address2")).toHaveFocus());
  });

  it("주소 검색을 못 불러오면 직접 입력할 수 있게 풀어요", async () => {
    delete window.daum;
    // 스크립트 태그를 붙이는 순간 실패한 것처럼 (jsdom 은 바깥 스크립트를 받지 않아요)
    const append = document.head.appendChild.bind(document.head);
    vi.spyOn(document.head, "appendChild").mockImplementation((node) => {
      if (node instanceof HTMLScriptElement) setTimeout(() => node.onerror?.(new Event("error")));
      return append(node);
    });
    const user = userEvent.setup();
    render(<CheckoutForm />);
    await user.click(screen.getByRole("button", { name: "주소 검색" }));
    expect(await screen.findByText("주소 검색을 불러오지 못했어요. 우편번호와 주소를 직접 입력해 주세요.")).toBeInTheDocument();
    expect(field("zipcode")).not.toHaveAttribute("readonly");
    await user.type(field("zipcode"), "12345");
    expect(field("zipcode")).toHaveValue("12345");
  });

  it("주문을 누르면 첫 번째 틀린 칸으로 커서가 가요", async () => {
    const user = userEvent.setup();
    render(<CheckoutForm />);
    await user.type(field("buyerName"), "김");
    await user.click(screen.getByRole("button", { name: "주문 완료하기" }));
    expect(field("phone")).toHaveFocus();
    expect(field("phone")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("우편번호 5자리를 입력해 주세요.")).toBeInTheDocument();
  });
});
