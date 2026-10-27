// 010-1234-5678 · 02-123-4567 처럼 하이픈을 넣어요 (숫자만 남겨서 다시 나눠요). 회원가입 · 주문서에서 같이 써요
export function formatPhone(value: string): string {
  const d = value.replace(/\D/g, "").slice(0, 11);
  const area = d.startsWith("02") ? 2 : 3; // 서울 02 만 두 자리
  const rest = d.slice(area);
  if (!rest) return d;
  if (rest.length <= 4) return `${d.slice(0, area)}-${rest}`;
  const mid = rest.length === 7 ? 3 : 4; // 가운데: 7자리 남으면 3 (010-123-4567), 아니면 4
  return `${d.slice(0, area)}-${rest.slice(0, mid)}-${rest.slice(mid)}`;
}
