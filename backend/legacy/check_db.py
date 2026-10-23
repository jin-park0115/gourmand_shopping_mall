from sqlalchemy import inspect

import models  # noqa: F401  모델을 불러와야 비교 대상에 등록됨
from database import Base, engine

inspector = inspect(engine)
problems = 0

for table in Base.metadata.sorted_tables:
    print(f"\n[{table.name}]")

    if not inspector.has_table(table.name):
        print("  ❌ DB에 이 테이블이 없습니다.")
        problems += 1
        continue

    db_columns = {col["name"]: col for col in inspector.get_columns(table.name)}

    for col in table.columns:
        if col.name not in db_columns:
            print(f"  ❌ {col.name}: DB에 없는 컬럼")
            problems += 1
            continue

        db_col = db_columns[col.name]
        print(f"  ✅ {col.name:<16} 모델: {str(col.type):<14} DB: {db_col['type']}")

        # 기본키가 자동 증가하는지 확인 (3단계 데이터 입력에 필요)
        if col.primary_key and not db_col.get("default") and not db_col.get("autoincrement"):
            print(f"     ⚠ {col.name}이 자동 증가가 아닐 수 있습니다.")

    for name in set(db_columns) - set(table.columns.keys()):
        print(f"  ⚠ {name}: DB에만 있는 컬럼 (모델에 없음)")

print(f"\n{'✅ 모델과 DB가 일치합니다.' if problems == 0 else f'❌ {problems}개의 불일치가 있습니다.'}")