"""SCRUM-25: 리뷰 API (목록 · 작성 · 수정 · 삭제, 테스트 DB). SCRUM-38 로그아웃 후 같은 토큰 401 포함."""
import pytest
from httpx import ASGITransport, AsyncClient

from database import get_session
from main import app
from tests.factories import make_product

pytestmark = pytest.mark.anyio

PASSWORD = "secret-123"
BODY = {"rating": 5, "content": "식감이 쫀득해서 아이들이 좋아해요."}


@pytest.fixture
async def client(db_session):
    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def product_id(db_session) -> int:
    return (await make_product(db_session, name="곤약젤리")).product_id


async def _auth(client, email: str = "kim@gourmand.com", name: str = "김구르") -> dict:
    await client.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": name})
    token = (await client.post("/auth/login", data={"username": email, "password": PASSWORD})).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_and_list(client, product_id) -> None:
    kim = await _auth(client)
    res = await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)

    assert res.status_code == 201
    review = res.json()
    assert (review["authorName"], review["rating"], review["isMine"], review["updatedAt"]) == ("김구르", 5, True, None)
    assert review["createdAt"].endswith("+09:00")  # KST

    listed = (await client.get(f"/products/{product_id}/reviews")).json()  # 비로그인
    assert (listed["total"], listed["page"], listed["size"], listed["pages"]) == (1, 1, 10, 1)
    assert listed["items"][0]["id"] == review["id"] and listed["items"][0]["isMine"] is False


async def test_is_mine_only_for_author(client, product_id) -> None:
    kim, lee = await _auth(client), await _auth(client, "lee@gourmand.com", "이망고")
    await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)
    await client.post(f"/products/{product_id}/reviews", json={**BODY, "rating": 3}, headers=lee)

    items = (await client.get(f"/products/{product_id}/reviews", headers=lee)).json()["items"]
    assert [(i["authorName"], i["isMine"]) for i in items] == [("이망고", True), ("김구르", False)]  # 최신순


async def test_list_pagination(client, product_id) -> None:
    for i in range(3):
        await client.post(f"/products/{product_id}/reviews", json=BODY, headers=await _auth(client, f"p{i}@test.com"))

    body = (await client.get(f"/products/{product_id}/reviews", params={"page": 2, "size": 2})).json()
    assert (body["total"], body["pages"], len(body["items"])) == (3, 2, 1)


async def test_duplicate_review_is_409(client, product_id) -> None:
    kim = await _auth(client)
    await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)
    res = await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)

    assert res.status_code == 409
    assert res.json() == {"code": "CONFLICT", "message": "이미 이 상품에 리뷰를 작성했어요."}
    assert (await client.get(f"/products/{product_id}/reviews")).json()["total"] == 1  # 그대로


@pytest.mark.parametrize(
    "body",
    [{"rating": 6, "content": BODY["content"]}, {"rating": 0, "content": BODY["content"]}, {"rating": 5, "content": "짧아요"},
     {"rating": 5, "content": "      공백만 길어      "}, {"rating": 5, "content": "가" * 1001}, {"content": BODY["content"]}],
)
async def test_invalid_body_is_422(client, product_id, body) -> None:
    res = await client.post(f"/products/{product_id}/reviews", json=body, headers=await _auth(client))
    assert res.status_code == 422 and res.json()["code"] == "VALIDATION_ERROR"


async def test_login_required(client, product_id) -> None:
    res = await client.post(f"/products/{product_id}/reviews", json=BODY)
    assert res.status_code == 401 and res.json()["code"] == "UNAUTHORIZED"


async def test_missing_product_or_review_is_404(client) -> None:
    kim = await _auth(client)
    assert (await client.get("/products/999999/reviews")).status_code == 404
    assert (await client.post("/products/999999/reviews", json=BODY, headers=kim)).status_code == 404
    res = await client.patch("/reviews/999999", json={"rating": 4}, headers=kim)
    assert res.status_code == 404 and res.json()["message"] == "리뷰를 찾을 수 없어요."
    assert (await client.delete("/reviews/999999", headers=kim)).status_code == 404


async def test_update_own_review(client, product_id) -> None:
    kim = await _auth(client)
    review_id = (await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)).json()["id"]

    res = await client.patch(f"/reviews/{review_id}", json={"rating": 3}, headers=kim)  # 보낸 값만
    assert res.status_code == 200
    body = res.json()
    assert (body["rating"], body["content"]) == (3, BODY["content"]) and body["updatedAt"] is not None

    assert (await client.patch(f"/reviews/{review_id}", json={}, headers=kim)).status_code == 422  # 바꿀 값 없음


async def test_others_review_is_403(client, product_id) -> None:
    kim, lee = await _auth(client), await _auth(client, "lee@gourmand.com", "이망고")
    review_id = (await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)).json()["id"]

    patch = await client.patch(f"/reviews/{review_id}", json={"rating": 1}, headers=lee)
    delete = await client.delete(f"/reviews/{review_id}", headers=lee)
    assert (patch.status_code, patch.json()["message"]) == (403, "본인이 작성한 리뷰만 수정할 수 있어요.")
    assert (delete.status_code, delete.json()["message"]) == (403, "본인이 작성한 리뷰만 삭제할 수 있어요.")
    assert (await client.get(f"/products/{product_id}/reviews")).json()["items"][0]["rating"] == 5  # 그대로


async def test_delete_then_write_again(client, product_id) -> None:
    kim = await _auth(client)
    review_id = (await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)).json()["id"]

    res = await client.delete(f"/reviews/{review_id}", headers=kim)
    assert res.status_code == 204 and res.content == b""
    assert (await client.get(f"/products/{product_id}/reviews")).json()["total"] == 0
    assert (await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)).status_code == 201  # 지우면 다시 쓸 수 있어요


async def test_product_rating_follows_reviews(client, product_id) -> None:
    kim, lee = await _auth(client), await _auth(client, "lee@gourmand.com", "이망고")
    await client.post(f"/products/{product_id}/reviews", json={**BODY, "rating": 5}, headers=kim)
    await client.post(f"/products/{product_id}/reviews", json={**BODY, "rating": 4}, headers=lee)

    product = (await client.get(f"/products/{product_id}")).json()
    assert (product["rating"], product["reviewCount"]) == (4.5, 2)


async def test_logged_out_token_cannot_write(client, product_id) -> None:
    """SCRUM-38: 로그인 → 보호 API 성공 → 로그아웃 → 같은 토큰 재요청 401."""
    kim = await _auth(client)
    first = await client.post(f"/products/{product_id}/reviews", json=BODY, headers=kim)
    assert first.status_code == 201

    assert (await client.post("/auth/logout", headers=kim)).status_code == 204

    res = await client.patch(f"/reviews/{first.json()['id']}", json={"rating": 1}, headers=kim)
    assert res.status_code == 401 and res.json()["code"] == "UNAUTHORIZED"
    # 공개 목록은 무효 토큰이어도 보여요 (isMine 만 false)
    listed = await client.get(f"/products/{product_id}/reviews", headers=kim)
    assert listed.status_code == 200 and listed.json()["items"][0]["isMine"] is False
