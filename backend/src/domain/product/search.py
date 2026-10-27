"""상품 검색 규칙 (순수 파이썬): 띄어쓰기 · 대소문자 무시, 자모 · 초성 비교, 작은 동의어 표.

- "도쿄 바나나" = "도쿄바나나", "POCKY" = "pocky"
- 한글을 자모로 풀어서 비교해요: "초코"(ㅊㅗㅋㅗ) 는 "초콜릿"(ㅊㅗㅋㅗㄹㄹㅣㅅ) 안에 있어요. 치는 중인 "곤야" 도 "곤약" 을 찾아요
- 검색어가 자음만이면 상품명의 초성과 비교해요: "ㄱㅇㅈㄹ" → 곤약젤리
- 표기가 다른 말은 동의어 표로: "초콜렛" → "초콜릿"
"""
import re

_BASE, _LAST = 0xAC00, 0xD7A3  # 가 ~ 힣
CHOSEONG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_JUNGSEONG = ["ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅗㅏ", "ㅗㅐ", "ㅗㅣ", "ㅛ", "ㅜ", "ㅜㅓ", "ㅜㅔ", "ㅜㅣ", "ㅠ", "ㅡ", "ㅡㅣ", "ㅣ"]
_JONGSEONG = ["", "ㄱ", "ㄲ", "ㄱㅅ", "ㄴ", "ㄴㅈ", "ㄴㅎ", "ㄷ", "ㄹ", "ㄹㄱ", "ㄹㅁ", "ㄹㅂ", "ㄹㅅ", "ㄹㅌ", "ㄹㅍ", "ㄹㅎ", "ㅁ", "ㅂ", "ㅂㅅ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]
# 겹모음 · 겹받침을 따로 친 경우도 같게 ("ㅘ" = "ㅗㅏ")
_COMPOUND = {"ㅘ": "ㅗㅏ", "ㅙ": "ㅗㅐ", "ㅚ": "ㅗㅣ", "ㅝ": "ㅜㅓ", "ㅞ": "ㅜㅔ", "ㅟ": "ㅜㅣ", "ㅢ": "ㅡㅣ",
             "ㄳ": "ㄱㅅ", "ㄵ": "ㄴㅈ", "ㄶ": "ㄴㅎ", "ㄺ": "ㄹㄱ", "ㄻ": "ㄹㅁ", "ㄼ": "ㄹㅂ", "ㄽ": "ㄹㅅ",
             "ㄾ": "ㄹㅌ", "ㄿ": "ㄹㅍ", "ㅀ": "ㄹㅎ", "ㅄ": "ㅂㅅ"}

# 사람들이 자주 다르게 치는 말 → 상품 정보에 쓰인 말
SYNONYMS = {
    "초콜렛": "초콜릿",
    "쵸콜릿": "초콜릿",
    "쵸콜렛": "초콜릿",
    "쵸코": "초코",
    "비스켓": "비스킷",
    "구미": "젤리",
}


def normalize(text: str) -> str:
    """소문자 + 공백 제거."""
    return re.sub(r"\s+", "", text).lower()


def to_jamo(text: str) -> str:
    """"초코" → "ㅊㅗㅋㅗ". 한글이 아닌 글자는 그대로."""
    out = []
    for ch in text:
        code = ord(ch)
        if _BASE <= code <= _LAST:
            i = code - _BASE
            out.append(CHOSEONG[i // 588] + _JUNGSEONG[(i % 588) // 28] + _JONGSEONG[i % 28])
        else:
            out.append(_COMPOUND.get(ch, ch))
    return "".join(out)


def to_choseong(text: str) -> str:
    """"곤약젤리" → "ㄱㅇㅈㄹ". 한글이 아닌 글자는 그대로."""
    return "".join(CHOSEONG[(ord(ch) - _BASE) // 588] if _BASE <= ord(ch) <= _LAST else ch for ch in text)


class SearchQuery:
    """검색어 하나를 미리 풀어 두고, 상품 글자와 비교해요."""

    def __init__(self, q: str):
        word = normalize(q)
        variants = {word}
        for wrong, right in SYNONYMS.items():
            if wrong in word:
                variants.add(word.replace(wrong, right))
        self.words = sorted(variants)
        # 자음만 친 검색어 ("ㄱㅇㅈㄹ") 는 초성 검색만 해요 (자모로 비교하면 받침 ㄱ + 다음 글자 ㅇ 같은 데서 엉뚱하게 걸려요)
        self.choseong = [w for w in self.words if w and all(ch in CHOSEONG for ch in w)]
        self.jamos = [to_jamo(w) for w in self.words if w not in self.choseong]

    def __bool__(self) -> bool:
        return any(self.words)

    def matches_name(self, name: str) -> bool:
        """상품명에서 찾았는지 (추천순에서 앞에 와요). 초성 검색은 상품명만 봐요."""
        text = normalize(name)
        return self._matches(text) or any(c in to_choseong(text) for c in self.choseong)

    def matches(self, *fields: str | None) -> bool:
        """상품명 · 나라 · 카테고리 · 제조사 · 식품유형 · 설명 중 어디서든 찾았는지."""
        return self._matches(normalize(" ".join(f for f in fields if f)))

    def _matches(self, text: str) -> bool:
        if any(w in text for w in self.words):
            return True
        jamo = to_jamo(text)
        return any(j in jamo for j in self.jamos)
