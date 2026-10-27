"""검색창 자동완성 GET /products/suggest (테스트 DB 에 시드 62개)."""
import pytest
from httpx import ASGITransport, AsyncClient

from core.config import Settings
from database import get_session
from infrastructure.seed import run_seed
from main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client(db_session):
    await run_seed(db_session, Settings(_env_file=None, admin_password="", customer_password=""))

    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _suggest(client, q, **params):
    res = await client.get("/products/suggest", params={"q": q, **params})
    assert res.status_code == 200, res.text
    return res.json()


async def test_products_categories_and_total(client) -> None:
    body = await _suggest(client, "초코")
    assert len(body["products"]) == 5 and body["total"] >= 8  # 5개만 보여 주고 전체 개수는 따로
    first = body["products"][0]
    assert set(first) == {"id", "name", "imageUrl", "price", "salePrice", "isSoldOut"}
    assert "초콜릿" in first["name"]
    assert [c["slug"] for c in body["categories"]] == ["chocolate"]  # 카테고리 "초콜릿"
    assert body["countries"] == []


async def test_choseong_and_country(client) -> None:
    assert [p["id"] for p in (await _suggest(client, "ㄱㅇㅈㄹ"))["products"]] == [3, 30]
    countries = (await _suggest(client, "일본"))["countries"]
    assert countries == [{"slug": "japan", "name": "일본"}]
    assert (await _suggest(client, "미국"))["countries"] == [{"slug": "other", "name": "미국"}]  # 4개국 밖은 '그 외'


async def test_limit_and_no_match(client) -> None:
    assert len((await _suggest(client, "젤리", limit=2))["products"]) == 2
    assert await _suggest(client, "없는과자이름") == {"total": 0, "products": [], "categories": [], "countries": []}
    assert await _suggest(client, "   ") == {"total": 0, "products": [], "categories": [], "countries": []}


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "가" * 51}, {"q": "초코", "limit": 11}])
async def test_invalid_is_422(client, params) -> None:
    assert (await client.get("/products/suggest", params=params)).status_code == 422


async def test_detail_route_still_works(client) -> None:
    assert (await client.get("/products/3")).status_code == 200  # suggest 를 앞에 둬도 상세는 그대로
