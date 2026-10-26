"""SCRUM-22 · 23: 상품 목록 · 상세 · 카테고리 API (테스트 DB 에 시드 60개, 테스트마다 rollback)."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from core.config import Settings
from database import get_session
from infrastructure.product.models import ProductModel
from infrastructure.review.models import ReviewModel
from infrastructure.seed import run_seed
from main import app
from tests.factories import make_member

pytestmark = pytest.mark.anyio

SOLD_OUT = {5, 15, 19}  # 시드에서 재고 0인 상품


@pytest.fixture
async def client(db_session):
    await run_seed(db_session, Settings(_env_file=None, admin_password="", customer_password=""))
    await db_session.execute(delete(ReviewModel))  # 시드 리뷰(SCRUM-25)는 빼고, 평점 · 리뷰 수는 테스트에서 직접 만들어요

    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _ids(client, **params) -> list[int]:
    res = await client.get("/products", params={"size": 100, **params})
    assert res.status_code == 200, res.text
    return [p["id"] for p in res.json()["items"]]


async def test_list_returns_page_in_camel_case(client) -> None:
    body = (await client.get("/products", params={"size": 7, "page": 2})).json()
    assert (body["total"], body["page"], body["size"], body["pages"]) == (60, 2, 7, 9)
    assert len(body["items"]) == 7
    konjac = (await client.get("/products/3")).json()
    assert konjac["discountPrice"] == 3900 and konjac["countrySlug"] == "japan" and konjac["categorySlug"] == "candy"
    assert konjac["rating"] == 0 and konjac["reviewCount"] == 0 and konjac["isSoldOut"] is False


@pytest.mark.parametrize("q", ["도쿄바나나", "도쿄 바나나", "  도쿄   바나나 "])
async def test_search_ignores_spaces(client, q) -> None:
    assert 4 in await _ids(client, q=q)


async def test_search_is_case_insensitive_and_literal(client) -> None:
    assert 41 in await _ids(client, q="oreo")  # OREO 오리지널
    # % _ 는 와일드카드가 아니라 글자예요. 와일드카드였다면 60개가 다 나왔을 거예요
    assert 9 in await _ids(client, q="100%")  # 9번 설명에 "100%" 가 있어요
    assert len(await _ids(client, q="%")) < 60 and len(await _ids(client, q="_")) < 60


async def test_filters(client) -> None:
    other = await _ids(client, country="other")
    assert len(other) == 20 and 41 in other and 1 not in other
    assert len(await _ids(client, country="japan")) == 10
    assert len(await _ids(client, category="snack")) == 16
    assert await _ids(client, category="nope") == []
    assert sorted(await _ids(client, ids="9,1,5,999")) == [1, 5, 9]
    both = await _ids(client, country="japan", category="candy")  # 조건은 AND
    assert 3 in both and 1 not in both and 58 not in both


@pytest.mark.parametrize("sort", ["recommend", "review", "low", "high", "new"])
async def test_sold_out_is_always_last(client, sort) -> None:
    ids = await _ids(client, sort=sort)
    assert len(ids) == 60 and set(ids[-3:]) == SOLD_OUT


async def test_price_sort_uses_sale_price(client) -> None:
    items = (await client.get("/products", params={"size": 100, "sort": "low"})).json()["items"]
    prices = [p["discountPrice"] if p["discountPrice"] is not None and p["discountPrice"] < p["price"] else p["price"] for p in items if not p["isSoldOut"]]
    assert prices == sorted(prices)
    high = (await client.get("/products", params={"size": 100, "sort": "high"})).json()["items"]
    high_prices = [p["discountPrice"] if p["discountPrice"] is not None and p["discountPrice"] < p["price"] else p["price"] for p in high if not p["isSoldOut"]]
    assert high_prices == sorted(prices, reverse=True)


async def test_new_sort_puts_new_products_first(client) -> None:
    items = (await client.get("/products", params={"size": 100, "sort": "new"})).json()["items"]
    flags = [p["isNew"] for p in items if not p["isSoldOut"]]
    assert flags == sorted(flags, reverse=True)


async def test_rating_and_review_sort(client, db_session) -> None:
    members = [(await make_member(db_session, email=f"r{i}@test.com", role="customer")).member_id for i in range(3)]
    db_session.add_all(
        [ReviewModel(product_id=2, member_id=m, rating=r, content="맛있어요 맛있어요") for m, r in zip(members, (5, 4, 4))]
        + [ReviewModel(product_id=6, member_id=members[0], rating=5, content="맛있어요 맛있어요")]
    )
    await db_session.flush()

    assert (await _ids(client, sort="review"))[:2] == [2, 6]
    assert (await _ids(client, sort="recommend"))[:2] == [6, 2]  # 평점 5.0 > 4.3
    detail = (await client.get("/products/2")).json()
    assert (detail["rating"], detail["reviewCount"]) == (4.3, 3)


async def test_recommend_puts_name_match_first(client, db_session) -> None:
    # 설명에만 '바나나' 가 들어간 상품보다 이름에 들어간 상품이 먼저
    product = await db_session.get(ProductModel, 1)
    product.description += " 바나나"
    await db_session.flush()
    ids = await _ids(client, q="바나나")
    assert ids.index(4) < ids.index(1)


@pytest.mark.parametrize(
    "params",
    [{"sort": "cheap"}, {"country": "korea"}, {"size": 500}, {"page": 0}, {"ids": "a,b"}, {"ids": "1,,2"}, {"q": "가" * 51}],
)
async def test_invalid_query_is_422(client, params) -> None:
    res = await client.get("/products", params=params)
    assert res.status_code == 422 and res.json()["code"] == "VALIDATION_ERROR"


async def test_detail_and_404(client) -> None:
    assert (await client.get("/products/4")).json()["name"] == "도쿄 바나나 4개입"
    res = await client.get("/products/999")
    assert res.status_code == 404 and res.json() == {"code": "NOT_FOUND", "message": "상품을 찾을 수 없어요."}
    assert (await client.get("/products/abc")).status_code == 422


async def test_categories_with_counts(client) -> None:
    body = (await client.get("/categories")).json()
    assert [(c["slug"], c["productCount"]) for c in body] == [
        ("snack", 16), ("cookie", 8), ("bakery", 11), ("chocolate", 7), ("candy", 12), ("savory", 6)
    ]
