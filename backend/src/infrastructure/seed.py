"""개발 · 시연용 시드 데이터 (SCRUM-15): 나라 · 카테고리 · 상품 60개 · 관리자/고객 계정.

여러 번 실행해도 중복이 생기지 않아요 (자연 키로 upsert).
- 나라 · 카테고리: 이름(UNIQUE)
- 상품: seed/products.json 의 id 를 product_id 로 그대로 써요 (프론트 상품 번호와 같게)
- 계정: 이메일(UNIQUE)
- 리뷰 (SCRUM-25): (상품, 회원) UNIQUE — 리뷰 작성용 회원 5명이 상품마다 0~5개씩 써요 (평점 · 리뷰 많은순 정렬 시연용)
실행: `uv run python scripts/seed.py`
"""
import json
import secrets
from dataclasses import dataclass
from pathlib import Path

from pwdlib import PasswordHash
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from infrastructure.auth.models import MemberModel
from infrastructure.product.models import CategoryModel, CountryModel, ProductModel
from infrastructure.review.models import ReviewModel

PRODUCTS_JSON = Path(__file__).resolve().parents[2] / "seed" / "products.json"

# 프론트 gourmand/lib/categories.ts 의 6개 분류와 같아요 (slug · 이름 · 상품 번호)
CATEGORIES: list[tuple[str, str, list[int]]] = [
    ("snack", "스낵·칩", [1, 2, 9, 12, 13, 16, 27, 28, 33, 34, 36, 39, 43, 44, 46, 48]),
    ("cookie", "쿠키·비스킷", [6, 23, 41, 49, 51, 52, 56, 60, 62]),
    ("bakery", "케이크·베이커리", [4, 11, 14, 18, 20, 29, 40, 47, 50, 53, 54]),
    ("chocolate", "초콜릿", [5, 7, 10, 32, 42, 45, 55, 61]),
    ("candy", "젤리·캔디", [3, 8, 15, 25, 26, 30, 31, 35, 37, 57, 58, 59]),
    ("savory", "육포·견과·별미", [17, 19, 21, 22, 24, 38]),
]

# docs/API.md 합의 2: 주요 4개국만 slug, 나머지는 NULL (API 에서 "other", domain/product/product.py)
COUNTRY_SLUGS: dict[str, str] = {"일본": "japan", "대만": "taiwan", "중국": "china", "베트남": "vietnam"}


# 리뷰 작성용 회원 (로그인할 일이 없어서 비밀번호는 아무도 모르는 임의 값)
REVIEWERS: list[tuple[str, str]] = [
    ("reviewer1@seed.test", "김구르"),
    ("reviewer2@seed.test", "이망고"),
    ("reviewer3@seed.test", "박쿠키"),
    ("reviewer4@seed.test", "최젤리"),
    ("reviewer5@seed.test", "정초코"),
]
REVIEW_RATINGS = [5, 4, 5, 3, 4, 5, 2]
REVIEW_CONTENTS = [
    "포장이 꼼꼼하고 맛도 기대 이상이에요.",
    "여행 가서 먹던 그 맛이라 반가웠어요.",
    "아이들 간식으로 주니 순식간에 없어졌어요.",
    "생각보다 달아서 커피랑 같이 먹으면 좋아요.",
    "선물용으로 샀는데 받는 사람이 좋아했어요.",
    "양이 조금 아쉽지만 맛은 확실해요.",
    "바삭한 식감이 오래가서 좋았어요.",
    "재구매 의사 있어요. 배송도 빨랐어요.",
]


def review_plan(product_ids: list[int]) -> list[tuple[int, int, int, str]]:
    """(상품 번호, 리뷰어 순번, 별점, 내용). 상품 번호로 정해져서 몇 번 실행해도 같아요."""
    return [
        (pid, i, REVIEW_RATINGS[(pid + i) % len(REVIEW_RATINGS)], REVIEW_CONTENTS[(pid * 3 + i) % len(REVIEW_CONTENTS)])
        for pid in product_ids
        for i in range(pid % (len(REVIEWERS) + 1))  # 상품마다 0~5개
    ]


@dataclass(frozen=True)
class SeedResult:
    countries: int
    categories: int
    products: int
    accounts: list[str]  # 만들거나 갱신한 계정 이메일
    skipped_accounts: list[str]  # 비밀번호가 없어서 건너뛴 계정 종류
    reviews: int = 0


def load_products(path: Path = PRODUCTS_JSON) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


async def run_seed(session: AsyncSession, settings: Settings, products: list[dict] | None = None) -> SeedResult:
    products = products if products is not None else load_products()
    category_of = {pid: name for _, name, ids in CATEGORIES for pid in ids}
    missing = [p["id"] for p in products if p["id"] not in category_of]
    if missing:
        raise ValueError(f"카테고리가 정해지지 않은 상품 번호가 있어요: {missing} (CATEGORIES 에 추가해 주세요)")

    country_ids = await _upsert_names(
        session,
        CountryModel,
        CountryModel.country_id,
        [{"name": name, "slug": COUNTRY_SLUGS.get(name)} for name in sorted({p["country"] for p in products})],
    )
    category_ids = await _upsert_names(
        session, CategoryModel, CategoryModel.category_id, [{"name": name, "slug": slug} for slug, name, _ in CATEGORIES]
    )

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

    reviews = await _seed_reviews(session, hasher, [p["id"] for p in products])
    await session.commit()
    return SeedResult(
        countries=len(country_ids),
        categories=len(category_ids),
        products=await session.scalar(select(func.count()).select_from(ProductModel)),
        accounts=accounts,
        skipped_accounts=skipped,
        reviews=reviews,
    )


async def _seed_reviews(session: AsyncSession, hasher: PasswordHash, product_ids: list[int]) -> int:
    member_stmt = insert(MemberModel).values(
        [{"email": e, "name": n, "role": "customer", "password_hash": hasher.hash(secrets.token_urlsafe(32))} for e, n in REVIEWERS]
    )
    await session.execute(member_stmt.on_conflict_do_nothing(index_elements=[MemberModel.email]))
    member_ids = dict(
        (await session.execute(select(MemberModel.email, MemberModel.member_id).where(MemberModel.email.in_([e for e, _ in REVIEWERS])))).all()
    )
    rows = [
        {"product_id": pid, "member_id": member_ids[REVIEWERS[i][0]], "rating": rating, "content": content}
        for pid, i, rating, content in review_plan(product_ids)
    ]
    if rows:
        stmt = insert(ReviewModel).values(rows)
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[ReviewModel.product_id, ReviewModel.member_id],
                set_={"rating": stmt.excluded.rating, "content": stmt.excluded.content},
            )
        )
    return len(rows)


async def _upsert_names(session: AsyncSession, model, id_column, values: list[dict]) -> dict[str, int]:
    """이름(UNIQUE)으로 upsert 하고 slug 는 늘 최신 값으로 맞춰요. {이름: id} 를 돌려줘요."""
    stmt = insert(model).values(values)
    await session.execute(stmt.on_conflict_do_update(index_elements=[model.name], set_={"slug": stmt.excluded.slug}))
    names = [v["name"] for v in values]
    rows = await session.execute(select(model.name, id_column).where(model.name.in_(names)))
    return dict(rows.all())
