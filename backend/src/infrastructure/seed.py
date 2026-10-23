"""개발 · 시연용 시드 데이터 (SCRUM-15): 나라 · 카테고리 · 상품 60개 · 관리자/고객 계정.

여러 번 실행해도 중복이 생기지 않아요 (자연 키로 upsert).
- 나라 · 카테고리: 이름(UNIQUE)
- 상품: seed/products.json 의 id 를 product_id 로 그대로 써요 (프론트 상품 번호와 같게)
- 계정: 이메일(UNIQUE)
실행: `uv run python scripts/seed.py`
"""
import json
from dataclasses import dataclass
from pathlib import Path

from pwdlib import PasswordHash
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from infrastructure.auth.models import MemberModel
from infrastructure.product.models import CategoryModel, CountryModel, ProductModel

PRODUCTS_JSON = Path(__file__).resolve().parents[2] / "seed" / "products.json"

# 프론트 gourmand/lib/categories.ts 의 6개 분류와 같아요 (slug · 이름 · 상품 번호)
CATEGORIES: list[tuple[str, str, list[int]]] = [
    ("snack", "스낵·칩", [1, 2, 9, 12, 13, 16, 27, 28, 33, 34, 36, 39, 43, 44, 46, 48]),
    ("cookie", "쿠키·비스킷", [6, 23, 41, 49, 51, 52, 56, 60]),
    ("bakery", "케이크·베이커리", [4, 11, 14, 18, 20, 29, 40, 47, 50, 53, 54]),
    ("chocolate", "초콜릿", [5, 7, 10, 32, 42, 45, 55]),
    ("candy", "젤리·캔디", [3, 8, 15, 25, 26, 30, 31, 35, 37, 57, 58, 59]),
    ("savory", "육포·견과·별미", [17, 19, 21, 22, 24, 38]),
]

# docs/API.md 합의 2: 주요 4개국만 slug, 나머지는 other
COUNTRY_SLUGS: dict[str, str] = {"일본": "japan", "대만": "taiwan", "중국": "china", "베트남": "vietnam"}
OTHER_COUNTRY_SLUG = "other"
# TODO(SCRUM-21): 박진 님 리비전으로 category.slug · country.slug 컬럼이 생기면
#   _upsert_names() 에서 slug 도 함께 넣어 주세요 (값은 위 CATEGORIES · COUNTRY_SLUGS).


@dataclass(frozen=True)
class SeedResult:
    countries: int
    categories: int
    products: int
    accounts: list[str]  # 만들거나 갱신한 계정 이메일
    skipped_accounts: list[str]  # 비밀번호가 없어서 건너뛴 계정 종류


def load_products(path: Path = PRODUCTS_JSON) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


async def run_seed(session: AsyncSession, settings: Settings, products: list[dict] | None = None) -> SeedResult:
    products = products if products is not None else load_products()
    category_of = {pid: name for _, name, ids in CATEGORIES for pid in ids}
    missing = [p["id"] for p in products if p["id"] not in category_of]
    if missing:
        raise ValueError(f"카테고리가 정해지지 않은 상품 번호가 있어요: {missing} (CATEGORIES 에 추가해 주세요)")

    country_ids = await _upsert_names(session, CountryModel, CountryModel.country_id, sorted({p["country"] for p in products}))
    category_ids = await _upsert_names(session, CategoryModel, CategoryModel.category_id, [name for _, name, _ in CATEGORIES])

    rows = [
        {
            "product_id": p["id"],
            "country_id": country_ids[p["country"]],
            "category_id": category_ids[category_of[p["id"]]],
            "name": p["name"],
            "manufacturer": p["manufacturer"],
            "description": p["description"],
            "price": p["price"],
            "discount_price": p.get("discountPrice"),
            "image_url": p["imageUrl"],
            "is_new": p["isNew"],
            "stock": p["stock"],
            "delivery_days": p["deliveryDays"],
            "volume": p["volume"],
            "unit": p["unit"],
            "item_count": p["itemCount"],
            "origin": p["origin"],
            "food_type": p["foodType"],
            "storage_method": p["storageMethod"],
        }
        for p in products
    ]
    stmt = insert(ProductModel).values(rows)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[ProductModel.product_id],
            set_={col: stmt.excluded[col] for col in rows[0] if col != "product_id"},
        )
    )
    # id 를 직접 넣었으니, 다음에 새 상품을 만들 때 번호가 겹치지 않게 시퀀스를 맞춰요
    await session.execute(
        text("SELECT setval(pg_get_serial_sequence('product', 'product_id'), (SELECT MAX(product_id) FROM product))")
    )

    accounts, skipped = [], []
    hasher = PasswordHash.recommended()  # argon2 (뼈대 pyproject 의 pwdlib[argon2])
    for kind, email, password, name, role in (
        ("admin", settings.admin_email, settings.admin_password, "관리자", "admin"),
        ("customer", settings.customer_email, settings.customer_password, "테스트 고객", "customer"),
    ):
        if not password:
            skipped.append(kind)
            continue
        member_stmt = insert(MemberModel).values(email=email, password_hash=hasher.hash(password), name=name, role=role)
        await session.execute(
            member_stmt.on_conflict_do_update(
                index_elements=[MemberModel.email],
                set_={"password_hash": member_stmt.excluded.password_hash, "role": role},
            )
        )
        accounts.append(email)

    await session.commit()
    return SeedResult(
        countries=len(country_ids),
        categories=len(category_ids),
        products=await session.scalar(select(func.count()).select_from(ProductModel)),
        accounts=accounts,
        skipped_accounts=skipped,
    )


async def _upsert_names(session: AsyncSession, model, id_column, names: list[str]) -> dict[str, int]:
    await session.execute(insert(model).values([{"name": n} for n in names]).on_conflict_do_nothing(index_elements=[model.name]))
    rows = await session.execute(select(model.name, id_column).where(model.name.in_(names)))
    return dict(rows.all())
