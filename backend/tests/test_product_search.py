"""상품 검색 규칙 (순수 파이썬): 자모 · 초성 · 동의어."""
import pytest

from domain.product.search import SearchQuery, normalize, to_choseong, to_jamo


def test_to_jamo_and_choseong() -> None:
    assert to_jamo("초코") == "ㅊㅗㅋㅗ"
    assert to_jamo("곤약") == "ㄱㅗㄴㅇㅑㄱ"
    assert to_jamo("과자") == "ㄱㅗㅏㅈㅏ"  # 겹모음은 풀어서
    assert to_jamo("닭") == "ㄷㅏㄹㄱ"  # 겹받침도
    assert to_jamo("ㅘ ab") == "ㅗㅏ ab"  # 한글이 아니거나 따로 친 자모
    assert to_choseong("곤약젤리 12개입") == "ㄱㅇㅈㄹ 12ㄱㅇ"
    assert normalize("  도쿄   바나나 ") == "도쿄바나나"


@pytest.mark.parametrize(
    ("q", "name"),
    [
        ("초코", "로이스 생초콜릿 오레"),  # 자모: ㅊㅗㅋㅗ ⊂ ㅊㅗㅋㅗㄹㄹㅣㅅ
        ("곤야", "오리히로 곤약젤리"),  # 받침 치기 전
        ("ㄱㅇㅈㄹ", "오리히로 곤약젤리"),  # 초성
        ("ㄷㅋ ㅂㄴㄴ", "도쿄 바나나 4개입"),  # 초성 + 띄어쓰기 무시
        ("초콜렛", "알포트 미니 초콜릿"),  # 동의어
        ("쵸코", "알포트 미니 초콜릿"),  # 동의어 → 초코 → 자모
        ("OREO", "oreo 오리지널"),
    ],
)
def test_name_matches(q, name) -> None:
    assert SearchQuery(q).matches_name(name)


@pytest.mark.parametrize(
    ("q", "name"),
    [
        ("ㄱㅇ", "약이 좋은 과자"),  # 자음만이면 자모로 비교하지 않아요 (받침 ㄱ + 이 → "ㄱㅇ" 오탐 방지)
        ("초콜릿", "초코파이"),  # 긴 말로 짧은 말은 못 찾아요
        ("ㅊㅋ", "웨이롱 곤약 젤리"),
    ],
)
def test_name_does_not_match(q, name) -> None:
    assert not SearchQuery(q).matches_name(name)


def test_other_fields_and_literal_characters() -> None:
    q = SearchQuery("일본")
    assert not q.matches_name("쟈가리코") and q.matches("쟈가리코", "일본", "스낵·칩")
    assert SearchQuery("100%").matches("감자", None, "감자 100% 사용")
    assert not SearchQuery("%").matches("감자", "감자 100 사용")


def test_blank_query_is_empty() -> None:
    assert not SearchQuery("   ")
