"""모든 기능이 함께 쓰는 응답 스키마 (docs/API.md 공통 규칙).

- CamelModel: 파이썬은 snake_case, JSON 은 camelCase (프론트 타입과 같게)
- Page[T]: 페이지 응답 { items, total, page, size, pages }
"""
from math import ceil

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


# DB 번호 칸(PostgreSQL integer)이 받을 수 있는 가장 큰 값. 이보다 큰 번호 · page 는 422 로 막아요 (DB 까지 가면 500)
MAX_ID = 2_147_483_647


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def of(cls, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        return cls(items=items, total=total, page=page, size=size, pages=ceil(total / size))
