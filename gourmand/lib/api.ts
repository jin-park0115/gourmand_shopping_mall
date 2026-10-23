// 백엔드 API 호출 (FastAPI, 기본 http://localhost:8000)
// 오류 응답 { code, message } 를 ApiError 로 바꿔서 던져요. 화면은 message 를 그대로 보여 주면 돼요.
// TODO(SCRUM-20): 로그인 토큰 첨부 · 401 이면 로그인 화면으로 이동을 여기에 더해요.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.code ?? "HTTP_ERROR", body.message ?? `요청에 실패했어요. (${res.status})`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

// 페이지 응답 (백엔드 presentation/schemas.py Page)
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
