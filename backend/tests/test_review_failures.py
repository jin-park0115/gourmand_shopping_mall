"""SCRUM-37 · 38: 상품 · 리뷰 API 실패 케이스 (401 · 403 · 404 · 405 · 409 · 422, 테스트 DB).

모든 실패가 같은 모양 { code, message } 이고, 실패한 요청은 DB 를 바꾸지 않는지 다시 조회해서 확인해요.
- 400 은 나지 않아요: 형식 오류는 공통 규칙대로 모두 422 VALIDATION_ERROR 예요 (깨진 JSON 테스트).
- 상품 API 는 공개라 401 · 403 이 없어요. 상품 404 · 422 는 아래와 test_product_api.py 에 있어요.
- 기본 실패(본문 422, 토큰 없음 401, 403, 404, 409)는 test_review_api.py 에도 있어요.
토큰은 진짜 회원가입 · 로그인 · 로그아웃을 거쳐서 받아요 (get_current_user 를 바꾸지 않아요).
"""
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from core.config import get_settings
from database import get_session
from infrastructure.review.models import ReviewModel
from main import app
from tests.factories import make_product

pytestmark = pytest.mark.anyio

PASSWORD = "secret-123"
BODY = {"rating": 5, "content": "식감이 쫀득해서 아이들이 좋아해요."}
BROKEN = "로그인 정보가 올바르지 않아요. 다시 로그인해 주세요."


@pytest.fixture
async def client(db_session):
    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def ctx(client, db_session) -> dict:
    """김구르가 곤약젤리에 쓴 리뷰 하나 + 이망고 토큰."""
    product_id = (await make_product(db_session, name="곤약젤리")).product_id
    kim, lee = await _auth(client, "kim@test.com", "김구르"), await _auth(client, "lee@test.com", "이망고")
    review_id = (await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)).json()["id"]
    return {"product": product_id, "review": review_id, "kim": kim, "lee": lee}


async def _auth(client, email: str, name: str) -> dict:
    await client.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": name})
    token = (await client.post("/auth/login", data={"username": email, "password": PASSWORD})).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _assert_error(res, status: int, code: str, message: str | None = None) -> None:
    body = res.json()
    assert res.status_code == status and body["code"] == code, res.text
    assert isinstance(body["message"], str) and body["message"]  # 화면이 그대로 보여 줄 문장
    if message is not None:
        assert body["message"] == message


async def _db_reviews(db_session, product_id: int) -> list[tuple[int, str]]:
    """DB 를 다시 조회한 (별점, 내용) 목록."""
    rows = await db_session.execute(
        select(ReviewModel.rating, ReviewModel.content).where(ReviewModel.product_id == product_id).order_by(ReviewModel.review_id)
    )
    return [tuple(r) for r in rows]


def _writes(ctx) -> list[tuple[str, str, dict | None]]:
    return [
        ("POST", f"/products/{ctx['product']}/reviews", BODY),
        ("PATCH", f"/reviews/{ctx['review']}", {"rating": 1}),
        ("DELETE", f"/reviews/{ctx['review']}", None),
    ]


# ── 401: 로그인이 안 됐거나 토큰을 믿을 수 없어요 ──


def _token(member_id: int, *, key: str | None = None, **claims) -> str:
    settings = get_settings()
    payload = {"sub": str(member_id), "role": "customer", "jti": "scrum-37", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    return jwt.encode({**payload, **claims}, key or settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.mark.parametrize(
    ("token", "message"),
    [
        (None, "로그인이 필요해요."),
        ("not-a-jwt", BROKEN),
        ("expired", "로그인이 만료됐어요. 다시 로그인해 주세요."),
        ("forged", BROKEN),  # 우리 서버 비밀키가 아닌 키로 서명
        ("unknown-member", BROKEN),  # 서명은 맞지만 없는 회원
    ],
)
async def test_401_on_every_write_and_db_untouched(client, db_session, ctx, token, message) -> None:
    kim_id = (await client.get("/auth/me", headers=ctx["kim"])).json()["id"]
    value = {
        None: None,
        "not-a-jwt": "not-a-jwt",
        "expired": _token(kim_id, exp=datetime.now(UTC) - timedelta(minutes=1)),
        "forged": _token(kim_id, key="another-secret-key-for-forged-token-32b"),
        "unknown-member": _token(999999),
    }[token]
    headers = {"Authorization": f"Bearer {value}"} if value else {}

    for method, path, body in _writes(ctx):
        res = await client.request(method, path, json=body, headers=headers)
        _assert_error(res, 401, "UNAUTHORIZED", message)
        assert res.headers["WWW-Authenticate"] == "Bearer"
    assert await _db_reviews(db_session, ctx["product"]) == [(5, BODY["content"])]


# ── 403: 남의 리뷰 ──


async def test_403_others_review_and_db_untouched(client, db_session, ctx) -> None:
    patch = await client.patch(f"/reviews/{ctx['review']}", json={"rating": 1, "content": "남이 바꾼 내용이에요 열 글자"}, headers=ctx["lee"])
    delete = await client.delete(f"/reviews/{ctx['review']}", headers=ctx["lee"])

    _assert_error(patch, 403, "FORBIDDEN", "본인이 작성한 리뷰만 수정할 수 있어요.")
    _assert_error(delete, 403, "FORBIDDEN", "본인이 작성한 리뷰만 삭제할 수 있어요.")
    assert await _db_reviews(db_session, ctx["product"]) == [(5, BODY["content"])]


# ── 404 · 405 ──


async def test_404_missing_product_review_or_path(client, ctx) -> None:
    lee = ctx["lee"]
    for res in [await client.get("/products/999999"), await client.get("/products/999999/reviews"),
                await client.post("/products/999999/reviews", json=BODY, headers=lee)]:
        _assert_error(res, 404, "NOT_FOUND", "상품을 찾을 수 없어요.")
    for res in [await client.patch("/reviews/999999", json={"rating": 4}, headers=lee),
                await client.delete("/reviews/999999", headers=lee)]:
        _assert_error(res, 404, "NOT_FOUND", "리뷰를 찾을 수 없어요.")
    _assert_error(await client.get("/review"), 404, "NOT_FOUND", "요청한 주소를 찾을 수 없어요.")


async def test_405_unsupported_method(client, ctx) -> None:
    res = await client.put(f"/reviews/{ctx['review']}", json=BODY, headers=ctx["kim"])
    _assert_error(res, 405, "METHOD_NOT_ALLOWED", "이 주소에서는 지원하지 않는 요청 방식이에요.")


# ── 409: 상품당 1인 1리뷰 ──


async def test_409_duplicate_and_db_untouched(client, db_session, ctx) -> None:
    res = await client.post(f"/products/{ctx['product']}/reviews", json={**BODY, "rating": 1}, headers=ctx["kim"])
    _assert_error(res, 409, "CONFLICT", "이미 이 상품에 리뷰를 작성했어요.")
    assert await _db_reviews(db_session, ctx["product"]) == [(5, BODY["content"])]


# ── 422: 형식 오류 ──


@pytest.mark.parametrize(
    "path",
    ["/products/abc", "/products/0", "/products/{product}/reviews?page=0", "/products/{product}/reviews?size=51",
     "/products/{product}/reviews?size=abc", "/products?sort=abc", "/products?size=101"],
)
async def test_422_bad_query_or_path(client, ctx, path) -> None:
    _assert_error(await client.get(path.format(**ctx)), 422, "VALIDATION_ERROR")


async def test_422_bad_review_id_or_empty_patch(client, ctx) -> None:
    _assert_error(await client.patch("/reviews/0", json={"rating": 4}, headers=ctx["kim"]), 422, "VALIDATION_ERROR")
    _assert_error(await client.patch(f"/reviews/{ctx['review']}", json={}, headers=ctx["kim"]), 422, "VALIDATION_ERROR")


async def test_422_not_400_for_broken_json(client, db_session, ctx) -> None:
    res = await client.post(
        f"/products/{ctx['product']}/reviews",
        content='{"rating": 5,'.encode(),  # 닫는 괄호가 없는 JSON
        headers={**ctx["lee"], "Content-Type": "application/json"},
    )
    _assert_error(res, 422, "VALIDATION_ERROR")
    assert len(await _db_reviews(db_session, ctx["product"])) == 1


# ── SCRUM-38: 로그아웃 후 같은 토큰 ──


async def test_logged_out_token_is_401_on_every_write(client, db_session, ctx) -> None:
    """로그인 → 보호 API 성공 → 로그아웃 → 같은 토큰으로 작성 · 수정 · 삭제 모두 401, DB 그대로."""
    kim = ctx["kim"]
    ok = await client.patch(f"/reviews/{ctx['review']}", json={"rating": 4}, headers=kim)
    assert ok.status_code == 200

    assert (await client.post("/auth/logout", headers=kim)).status_code == 204

    for method, path, body in _writes(ctx):
        res = await client.request(method, path, json=body, headers=kim)
        _assert_error(res, 401, "UNAUTHORIZED", "로그아웃된 토큰이에요. 다시 로그인해 주세요.")
    _assert_error(await client.get("/auth/me", headers=kim), 401, "UNAUTHORIZED")
    assert await _db_reviews(db_session, ctx["product"]) == [(4, BODY["content"])]

    # 공개 목록 · 상품은 계속 보여요 (isMine 만 false)
    listed = await client.get(f"/products/{ctx['product']}/reviews", headers=kim)
    assert listed.status_code == 200 and listed.json()["items"][0]["isMine"] is False
    assert (await client.get(f"/products/{ctx['product']}", headers=kim)).status_code == 200

    # 다시 로그인하면 새 토큰으로 돼요
    again = await _auth(client, "kim@test.com", "김구르")
    assert (await client.delete(f"/reviews/{ctx['review']}", headers=again)).status_code == 204
    assert await _db_reviews(db_session, ctx["product"]) == []
