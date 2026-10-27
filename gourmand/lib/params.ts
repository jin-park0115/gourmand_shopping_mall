// 주소 쿼리 읽기: ?q=a&q=b 처럼 같은 이름이 여러 번 오면 Next 는 배열(["a", "b"])로 줘요.
// 화면은 글자 하나를 기대하니까 첫 번째 값만 써요 (배열에 .trim() 하면 페이지가 오류 화면이 돼요)
type Raw = Record<string, string | string[] | undefined>;

export function firstParams<K extends string>(params: Raw, ...keys: K[]): Partial<Record<K, string>> {
  const out: Partial<Record<K, string>> = {};
  for (const key of keys) {
    const value = params[key];
    const first = Array.isArray(value) ? value[0] : value;
    if (first !== undefined) out[key] = first;
  }
  return out;
}
