# 구르망 프론트엔드 (Next.js 16)

## 실행

```bash
cd gourmand
npm install
copy .env.example .env.local   # (macOS/Linux: cp) 백엔드 주소, 기본 http://localhost:8000
npm run dev                    # http://localhost:3000
```

상품 화면은 백엔드 API 에서 데이터를 받아요. 먼저 백엔드를 띄우고 시드를 넣어 주세요 (`backend/README.md`).
백엔드가 꺼져 있으면 상품 화면은 오류 화면(`app/error.tsx`)을 보여 줘요.

## 데이터 흐름

| 파일 | 역할 |
| --- | --- |
| `lib/api.ts` | 백엔드 호출 (`NEXT_PUBLIC_API_URL`), 오류 `{code, message}` → `ApiError`, 로그인 토큰 자동 첨부 |
| `lib/auth.ts` · `components/AuthProvider.tsx` | 회원가입 · 로그인 · 로그아웃 · 내 정보, 화면 전체의 로그인 상태 (`useAuth()`) |
| `lib/products.ts` | `fetchProducts` · `fetchProduct` · `fetchCategoryCounts`, 판매가 · 할인율 같은 계산 |
| `lib/categories.ts` | 카테고리 6개의 화면 꾸밈 (이름 · 소개 · 대표 사진). 상품이 어느 카테고리인지는 DB 가 정해요 |
| `lib/adminOrders.ts` | 관리자 주문 API (`/admin/orders` 목록 · 요약 · 상세 · 상태 변경, SCRUM-36). 관리자 토큰이 있어야 해요 |
| `data/products.ts` | 옛 정적 데이터. 화면은 더 안 쓰고, 상품 내보내기 · 검사 스크립트(`scripts/`)만 써요 |

## 렌더링 결정 (SCRUM-24): 상품 페이지는 요청할 때 렌더링

`generateStaticParams` 로 상품 · 나라 · 카테고리 페이지를 빌드 때 미리 만들던 것을 없앴어요.

- **재고 · 품절이 주문마다 바뀌어요.** 빌드 때 만든 페이지는 품절을 늦게 보여 줘요.
- **리뷰를 쓰면 평점이 바로 바뀌어야 해요** (SCRUM-25).
- **빌드가 백엔드에 묶이지 않아요.** `npm run build` 는 백엔드 없이도 돼요.

`cacheComponents` 를 켜 둬서, 데이터를 받는 부분은 `<Suspense>` 안에 두고 페이지 틀(배너 · 메뉴)은 미리 만들어져요.
데이터는 `use cache` 없이 매번 받아요. 상품이 많아져 느려지면 목록에 `use cache` + `cacheLife('minutes')` 를 붙이면 돼요.

알아 둘 점: 없는 상품(`/products/999`)은 not-found 화면이 나오지만, 화면을 흘려 보내는(streaming) 방식이라 HTTP 상태는 200이에요.

## 로그인 (SCRUM-20)

- 화면: `/login`, `/signup` (가입하면 바로 로그인). `?next=/cart` 처럼 돌아갈 주소를 받아요 (우리 사이트 주소만)
- 로그인 후 부르는 API 는 `api()` 가 `Authorization: Bearer` 를 붙여요. 화면에서 따로 할 일이 없어요
  ```ts
  import { api } from "@/lib/api";
  const orders = await api<Page<AdminOrder>>("/admin/orders?status=배송중");
  ```
- **401** (만료 · 로그아웃된 토큰): 토큰을 지우고 `/login?next=지금주소` 로 이동해요
- **403** (고객이 관리자 API 호출 등): 이동하지 않고 `ApiError` 로 던져요 → 화면에서 `err.status === 403` 이면 안내
- 로그인 상태가 필요한 화면은 `const { member, ready } = useAuth()` (`ready` 전에는 확인 중)

**토큰 저장 위치: localStorage.** 장바구니 · 주문 · 리뷰 · 관리자 화면이 모두 클라이언트 컴포넌트라 가장 단순해요.
화면에 악성 스크립트가 들어오면(XSS) 토큰이 읽힐 수 있는 한계가 있어요. 바꿀 때는 `lib/api.ts` 의 `getToken` · `setToken` 과
백엔드 로그인만 고치면 돼요 (httpOnly 쿠키로 발급하거나, Next 가 중간에서 API 를 전달하는 방식).
