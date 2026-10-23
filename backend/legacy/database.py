import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL이 설정되지 않았습니다. backend/.env 파일을 확인하세요.")

# pool_pre_ping: 끊어진 연결을 미리 확인해서 다시 연결
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"options": "-csearch_path=gourmand"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


# API 요청마다 DB 세션을 열고, 끝나면 닫아 주는 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()