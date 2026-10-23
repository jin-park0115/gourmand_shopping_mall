"""SCRUM-21: 상품 Repository 가 도메인 객체를 돌려주는지 (테스트 DB, 테스트마다 rollback)."""
import pytest

from domain.product.product import Product
from infrastructure.product.models import ProductModel
from infrastructure.product.repositories import ProductRepository
from tests.factories import make_product

pytestmark = pytest.mark.anyio


async def test_get_returns_domain_object(db_session) -> None:
    row = await make_product(db_session, name="로투스", price=4500, stock=7)
    row.country.slug = "japan"

    product = await ProductRepository(db_session).get(row.product_id)

    assert isinstance(product, Product)
    assert (product.id, product.name, product.price, product.stock) == (row.product_id, "로투스", 4500, 7)
    assert (product.country_slug, product.category_slug) == ("japan", "cat-로투스")


async def test_country_without_slug_is_other(db_session) -> None:
    row = await make_product(db_session)  # factory 나라는 slug 가 없어요
    assert (await ProductRepository(db_session).get(row.product_id)).country_slug == "other"


async def test_missing_product_is_none(db_session) -> None:
    repo = ProductRepository(db_session)
    assert await repo.get(999_999) is None
    assert await repo.get_for_update(999_999) is None


async def test_stock_change_is_saved(db_session) -> None:
    product_id = (await make_product(db_session, stock=10)).product_id
    repo = ProductRepository(db_session)

    product = await repo.get_for_update(product_id)
    product.decrease_stock(3)
    await repo.save_stock(product)

    db_session.expire_all()
    assert (await db_session.get(ProductModel, product_id)).stock == 7
