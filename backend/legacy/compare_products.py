import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from database import SessionLocal
from models import Category, Country, Product, Review

SEED_DIR = Path(__file__).parent / "seed"
MOCK_FILE = SEED_DIR / "products.json"
OUT_JSON = SEED_DIR / "products.from-db.json"
OUT_TS = SEED_DIR / "products.from-db.ts"

# 직접 저장된 값 (반드시 같아야 함)
FIELDS = [
    "name", "price", "country", "category", "imageUrl", "description", "isNew",
    "discountPrice", "stock", "isSoldOut", "deliveryDays", "volume", "unit",
    "itemCount", "origin", "foodType", "manufacturer", "storageMethod",
]
# review 테이블에서 계산되는 값 (달라도 될 수 있음)
DERIVED = ["rating", "reviewCount"]


def norm(value):
    """DB의 Decimal과 목업의 숫자를 같은 형태로 맞춘다. (4.0 → 4)"""
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def load_db_products() -> list[dict]:
    """DB 데이터를 프론트의 Product 모양으로 변환한다. (4단계 API와 같은 로직)"""
    stmt = (
        select(
            Product,
            Country.name,
            Category.name,
            func.coalesce(func.round(func.avg(Review.rating), 1), 0),
            func.count(Review.review_id),
        )
        .join(Country, Product.country_id == Country.country_id)
        .join(Category, Product.category_id == Category.category_id)
        .outerjoin(Review, Review.product_id == Product.product_id)
        .group_by(Product.product_id, Country.name, Category.name)
        .order_by(Product.product_id)
    )

    with SessionLocal() as db:
        rows = db.execute(stmt).all()

    products = []
    for p, country, category, rating, review_count in rows:
        item = {
            "id": p.product_id,
            "name": p.name,
            "price": norm(p.price),
            "country": country,
            "category": category,
            "imageUrl": p.image_url,
            "description": p.description,
            "isNew": bool(p.is_new),
            "discountPrice": norm(p.discount_price),
            "rating": norm(rating),
            "reviewCount": review_count,
            "stock": norm(p.stock),
            "isSoldOut": p.stock == 0,
            "deliveryDays": norm(p.delivery_days),
            "volume": norm(p.volume),
            "unit": p.unit,
            "itemCount": norm(p.item_count),
            "origin": p.origin,
            "foodType": p.food_type,
            "manufacturer": p.manufacturer,
            "storageMethod": p.storage_method,
        }
        if item["discountPrice"] is None:
            del item["discountPrice"]  # 프론트 규격에서 선택 속성이므로 없으면 생략
        products.append(item)
    return products


def load_mock_products() -> list[dict]:
    return json.loads(MOCK_FILE.read_text(encoding="utf-8"))


def get(item: dict, field: str):
    """선택 속성의 기본값을 맞춰서 비교한다. (isNew 없음 = False)"""
    if field == "isNew":
        return bool(item.get("isNew", False))
    return norm(item.get(field))


def show(value) -> str:
    return "(없음)" if value is None else repr(value)


def main():
    db_items = {p["id"]: p for p in load_db_products()}
    mock_items = {p["id"]: p for p in load_mock_products()}

    print(f"=== 상품 개수 ===\nDB {len(db_items)}개 / 목업 {len(mock_items)}개")

    only_db = sorted(set(db_items) - set(mock_items))
    only_mock = sorted(set(mock_items) - set(db_items))
    if only_db:
        print("\n=== DB에만 있는 상품 ===")
        for i in only_db:
            print(f"  id {i} {db_items[i]['name']}")
    if only_mock:
        print("\n=== 목업에만 있는 상품 ===")
        for i in only_mock:
            print(f"  id {i} {mock_items[i]['name']}")

    diff_count = 0
    derived_lines = []
    print("\n=== 값이 다른 항목 ===")
    for i in sorted(set(db_items) & set(mock_items)):
        db_p, mock_p = db_items[i], mock_items[i]
        lines = [
            f"  {field:<15} DB: {show(get(db_p, field))}  /  목업: {show(get(mock_p, field))}"
            for field in FIELDS
            if get(db_p, field) != get(mock_p, field)
        ]
        if lines:
            diff_count += len(lines)
            print(f"[id {i} {db_p['name']}]")
            print("\n".join(lines))

        for field in DERIVED:
            if get(db_p, field) != get(mock_p, field):
                derived_lines.append(
                    f"  id {i:<4} {field:<12} DB: {show(get(db_p, field))}  /  목업: {show(get(mock_p, field))}"
                )
    if diff_count == 0:
        print("  없음 ✅")

    if derived_lines:
        print("\n=== 참고: 리뷰에서 계산되는 값의 차이 ===")
        print("\n".join(derived_lines))

    # DB 데이터를 Product 모양으로 저장 (목업 교체용)
    db_list = list(db_items.values())
    OUT_JSON.write_text(json.dumps(db_list, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_TS.write_text(
        "import { Product } from '@/types/product';\n\n"
        "// PostgreSQL gourmand 스키마에서 생성한 상품 데이터\n"
        f"export const products: Product[] = {json.dumps(db_list, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )

    print(f"\n=== 요약 ===")
    print(f"DB에만 {len(only_db)}개, 목업에만 {len(only_mock)}개, 값이 다른 항목 {diff_count}개")
    print(f"DB 데이터를 {OUT_TS.name}, {OUT_JSON.name}로 저장했습니다.")


if __name__ == "__main__":
    main()