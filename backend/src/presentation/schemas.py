"""모든 기능이 함께 쓰는 응답 스키마 (docs/API.md 공통 규칙).

- CamelModel: 파이썬은 snake_case, JSON 은 camelCase (프론트 타입과 같게)
- Page[T]: 페이지 응답 { items, total, page, size, pages }
"""
from math import ceil

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


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
