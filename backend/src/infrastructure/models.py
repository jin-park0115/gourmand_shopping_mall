"""모든 ORM 모델을 한곳에서 import 해 Base.metadata 에 등록합니다 (테이블 생성용).

새 기능의 models.py 를 만들면 여기에 한 줄 추가하세요.
"""
from infrastructure.admin import models as _admin  # noqa: F401
from infrastructure.auth import models as _auth  # noqa: F401
from infrastructure.cart import models as _cart  # noqa: F401
from infrastructure.order import models as _order  # noqa: F401
from infrastructure.product import models as _product  # noqa: F401
from infrastructure.review import models as _review  # noqa: F401
