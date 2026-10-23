"""SCRUM-15: 시드 데이터 (테스트 DB, 테스트마다 rollback)."""
import pytest
from pwdlib import PasswordHash
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import func, select

from core.config import Settings
from infrastructure.auth.models import MemberModel
from infrastructure.product.models import CategoryModel, CountryModel, ProductModel
from infrastructure.seed import CATEGORIES, load_products, run_seed

pytestmark = pytest.mark.anyio

SETTINGS = Settings(
    _env_file=None,
    admin_email="admin@seed.test",
    admin_password="admin-pass-1",
    customer_email="customer@seed.test",
    customer_password="customer-pass-1",
)


async def _count(session, model) -> int:
    return await session.scalar(select(func.count()).select_from(model))


def test_default_seed_emails_pass_email_validation() -> None:
    # 로그인 · 회원 스키마가 EmailStr 을 쓰면 .local 같은 특수 도메인은 거부돼요
    defaults = Settings(_env_file=None)
    for email in (defaults.admin_email, defaults.customer_email):
        TypeAdapter(EmailStr).validate_python(email)


def test_every_product_has_a_category() -> None:
    ids = {p["id"] for p in load_products()}
    mapped = [pid for _, _, pids in CATEGORIES for pid in pids]
    assert len(ids) == 60
    assert sorted(mapped) == sorted(ids)  # 빠짐도 겹침도 없어요


async def test_seed_creates_everything(db_session) -> None:
    result = await run_seed(db_session, SETTINGS)
    assert (result.countries, result.categories, result.products) == (6, 6, 60)
    assert result.accounts == ["admin@seed.test", "customer@seed.test"] and result.skipped_accounts == []
    assert await _count(db_session, CountryModel) == 6
    assert sorted(await db_session.scalars(select(CategoryModel.name))) == sorted(name for _, name, _ in CATEGORIES)

    jagarico = await db_session.get(ProductModel, 1)
    assert jagarico.name == "쟈가리코 샐러드맛" and jagarico.price == 3200 and jagarico.discount_price is None
    assert (await db_session.get(CategoryModel, jagarico.category_id)).name == "스낵·칩"
    assert (await db_session.get(CountryModel, jagarico.country_id)).name == "일본"
    assert dict((await db_session.execute(select(CategoryModel.name, CategoryModel.slug))).all())["스낵·칩"] == "snack"
    country_slugs = dict((await db_session.execute(select(CountryModel.name, CountryModel.slug))).all())
    assert country_slugs["일본"] == "japan"
    assert all(slug is None for name, slug in country_slugs.items() if name not in ("일본", "대만", "중국", "베트남"))
    konjac = await db_session.get(ProductModel, 3)
    assert konjac.discount_price == 3900


async def test_accounts_use_argon2_and_roles(db_session) -> None:
    await run_seed(db_session, SETTINGS)
    admin = await db_session.scalar(select(MemberModel).where(MemberModel.email == "admin@seed.test"))
    customer = await db_session.scalar(select(MemberModel).where(MemberModel.email == "customer@seed.test"))
    assert (admin.role, customer.role) == ("admin", "customer")
    assert admin.password_hash.startswith("$argon2")
    assert "admin-pass-1" not in admin.password_hash
    assert PasswordHash.recommended().verify("admin-pass-1", admin.password_hash)


async def test_running_twice_does_not_duplicate(db_session) -> None:
    await run_seed(db_session, SETTINGS)
    products = load_products()
    products[0] = {**products[0], "price": 3500}  # 데이터가 바뀌면 덮어써요
    again = await run_seed(db_session, SETTINGS, products)
    assert again.products == 60
    assert await _count(db_session, CountryModel) == 6
    assert await _count(db_session, CategoryModel) == 6
    assert await _count(db_session, MemberModel) == 2
    db_session.expire_all()
    assert (await db_session.get(ProductModel, 1)).price == 3500


async def test_new_product_after_seed_gets_next_id(db_session) -> None:
    await run_seed(db_session, SETTINGS)
    jagarico = await db_session.get(ProductModel, 1)
    new = ProductModel(
        country_id=jagarico.country_id, category_id=jagarico.category_id, name="새 상품", manufacturer="m",
        description="d", price=1000, image_url="/x.png", stock=1, delivery_days=1, volume=1, unit="g",
        origin="o", food_type="f", storage_method="s",
    )
    db_session.add(new)
    await db_session.flush()
    assert new.product_id == 61  # 시퀀스를 맞춰서 1번과 겹치지 않아요


async def test_accounts_skipped_without_password(db_session) -> None:
    result = await run_seed(db_session, Settings(_env_file=None))
    assert result.accounts == [] and result.skipped_accounts == ["admin", "customer"]
    assert await _count(db_session, MemberModel) == 0
    assert result.products == 60
