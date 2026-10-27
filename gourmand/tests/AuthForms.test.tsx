import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { router, searchParams } from "./next-mocks";
import { LoginForm, SignupForm } from "@/components/AuthForms";
import { ApiError } from "@/lib/api";
import { login, signup } from "@/lib/auth";
import { formatPhone } from "@/lib/phone";

vi.mock("@/lib/auth", async (original) => ({
  ...(await original<typeof import("@/lib/auth")>()),
  login: vi.fn(),
  signup: vi.fn(),
}));

// 레이블에 버튼 · 오류 문구가 함께 들어가서 name 으로 찾아요
const field = (name: string) => document.querySelector<HTMLInputElement>(`[name=${name}]`)!;

const customer = { id: 1, email: "kim@test.com", name: "김", phone: null, role: "customer" as const };

beforeEach(() => {
  router.replace.mockClear();
  searchParams.value = new URLSearchParams();
  vi.mocked(login).mockReset();
  vi.mocked(signup).mockReset();
});

describe("formatPhone: 연락처 하이픈", () => {
  it.each([
    ["010", "010"],
    ["0101234", "010-1234"],
    ["01012345678", "010-1234-5678"],
    ["0101234567", "010-123-4567"],
    ["021234567", "02-123-4567"],
    ["0212345678", "02-1234-5678"],
    ["010-1234-5678", "010-1234-5678"], // 이미 하이픈이 있어도
    ["010abc12345678999", "010-1234-5678"], // 숫자만, 11자리까지
  ])("%s → %s", (input, expected) => {
    expect(formatPhone(input)).toBe(expected);
  });
});

describe("회원가입 폼", () => {
  const fill = async (user: ReturnType<typeof userEvent.setup>, confirm = "secret-123") => {
    await user.type(field("email"), "kim@test.com");
    await user.type(field("password"), "secret-123");
    await user.type(field("passwordConfirm"), confirm);
    await user.type(field("name"), " 김 ");
  };
  const submit = () => screen.getByRole("button", { name: "가입하고 로그인" });

  it("비밀번호 확인이 다르면 알려 주고 가입 버튼을 막아요", async () => {
    const user = userEvent.setup();
    render(<SignupForm />);
    await fill(user, "secret-124");
    expect(screen.getByText("비밀번호가 달라요.")).toBeInTheDocument();
    expect(submit()).toBeDisabled();
  });

  it("같으면 초록 안내, 가입하면 고객은 원래 보던 주소로", async () => {
    vi.mocked(signup).mockResolvedValue(customer);
    searchParams.value = new URLSearchParams("next=/cart");
    const user = userEvent.setup();
    render(<SignupForm />);
    await fill(user);
    expect(screen.getByText("비밀번호가 같아요 ✓")).toBeInTheDocument();
    await user.click(submit());
    expect(signup).toHaveBeenCalledWith({ email: "kim@test.com", password: "secret-123", name: "김", phone: undefined });
    expect(router.replace).toHaveBeenCalledWith("/cart");
  });

  it("연락처는 치는 대로 하이픈이 들어가요", async () => {
    const user = userEvent.setup();
    render(<SignupForm />);
    await user.type(field("phone"), "01012345678");
    expect(field("phone")).toHaveValue("010-1234-5678");
  });

  it("보기를 누르면 비밀번호가 보여요 (확인 칸도 같이)", async () => {
    const user = userEvent.setup();
    render(<SignupForm />);
    await user.click(screen.getByRole("button", { name: "보기" }));
    expect(field("password")).toHaveAttribute("type", "text");
    expect(field("passwordConfirm")).toHaveAttribute("type", "text");
  });

  it.each([
    ["email: 이메일 형식이 올바르지 않아요.", "email", "이메일 형식이 올바르지 않아요."],
    ["이미 가입된 이메일이에요.", "email", "이미 가입된 이메일이에요."],
    ["name: 50자 이하로 입력해 주세요.", "name", "50자 이하로 입력해 주세요."],
  ])("서버 오류 '%s' → %s 칸 아래에", async (message, name, shown) => {
    vi.mocked(signup).mockRejectedValue(new ApiError(422, "VALIDATION_ERROR", message));
    const user = userEvent.setup();
    render(<SignupForm />);
    await fill(user);
    await user.click(submit());
    const input = field(name);
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input.closest("label")).toHaveTextContent(shown);
    await user.type(input, "x"); // 고치기 시작하면 지워져요
    expect(input).not.toHaveAttribute("aria-invalid");
  });

  it("어느 칸인지 모르는 오류 · 연결 실패는 맨 아래 상자에", async () => {
    vi.mocked(signup).mockRejectedValue(new TypeError("Failed to fetch"));
    const user = userEvent.setup();
    render(<SignupForm />);
    await fill(user);
    await user.click(submit());
    expect(screen.getByRole("alert")).toHaveTextContent("서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.");
    expect(submit()).toBeEnabled(); // 다시 누를 수 있어요
  });
});

describe("로그인 폼", () => {
  const loginWith = async (password: string) => {
    const user = userEvent.setup();
    render(<LoginForm />);
    await user.type(screen.getByLabelText("이메일"), "kim@test.com");
    await user.type(screen.getByLabelText("비밀번호"), password);
    await user.click(screen.getByRole("button", { name: "로그인" }));
  };

  it("관리자는 관리자 화면으로", async () => {
    vi.mocked(login).mockResolvedValue({ ...customer, role: "admin" });
    searchParams.value = new URLSearchParams("next=/cart");
    await loginWith("secret-123");
    expect(router.replace).toHaveBeenCalledWith("/admin");
  });

  it("외부 주소 next 는 버리고 홈으로", async () => {
    vi.mocked(login).mockResolvedValue(customer);
    searchParams.value = new URLSearchParams("next=//evil.com");
    await loginWith("secret-123");
    expect(router.replace).toHaveBeenCalledWith("/");
  });

  it("외부 주소 next 는 회원가입 링크에도 안 붙여요", () => {
    searchParams.value = new URLSearchParams("next=/\\evil.com");
    render(<LoginForm />);
    expect(screen.getByRole("link", { name: "회원가입" })).toHaveAttribute("href", "/signup");
  });

  it.each([
    [401, "UNAUTHORIZED", "이메일 또는 비밀번호가 올바르지 않아요."],
    [429, "TOO_MANY_REQUESTS", "로그인을 5번 잘못 시도해서 잠시 막았어요. 10분 뒤에 다시 시도해 주세요."],
  ])("%i 는 서버 문구를 그대로 보여 줘요", async (status, code, message) => {
    vi.mocked(login).mockRejectedValue(new ApiError(status, code, message));
    await loginWith("wrong");
    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(router.replace).not.toHaveBeenCalled();
  });
});
