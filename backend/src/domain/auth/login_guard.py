"""로그인 연속 실패 잠금 (순수 파이썬).

같은 이메일로 WINDOW 안에 MAX_FAILURES 번 틀리면 LOCK 동안 로그인을 막아요 (비밀번호를 대입해 보는 공격 방지).
그동안은 비밀번호가 맞아도 막혀요. 로그인에 성공하면 실패 기록을 지워요.

ponytail: 서버 메모리에 기록해요. 서버를 다시 켜면 지워지고, 서버가 여러 대면 대마다 따로 세요.
  여러 대로 늘리면 Redis · DB 로 옮겨요. IP 기준 제한은 프록시(Render) 뒤라 실제 IP 를 믿을 수 있게 한 뒤에 추가해요.
"""
import time
from collections.abc import Callable
from math import ceil

from domain.exceptions import TooManyRequestsError

MAX_FAILURES = 5
WINDOW_SECONDS = 10 * 60
LOCK_SECONDS = 10 * 60
MAX_TRACKED = 10_000  # 기록하는 이메일 수가 이만큼 넘으면 오래된 기록부터 정리 (메모리가 끝없이 늘지 않게)


class LoginGuard:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._failures: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}

    def check(self, key: str) -> None:
        """잠겨 있으면 429. 로그인 시도 전에 불러요."""
        until = self._locked_until.get(key)
        if until is None:
            return
        left = until - self._clock()
        if left <= 0:
            del self._locked_until[key]
            return
        raise TooManyRequestsError(
            f"로그인을 {MAX_FAILURES}번 잘못 시도해서 잠시 막았어요. {ceil(left / 60)}분 뒤에 다시 시도해 주세요."
        )

    def failed(self, key: str) -> None:
        now = self._clock()
        recent = [t for t in self._failures.get(key, []) if now - t < WINDOW_SECONDS]
        recent.append(now)
        if len(recent) >= MAX_FAILURES:
            self._locked_until[key] = now + LOCK_SECONDS
            recent = []
        self._failures[key] = recent
        if len(self._failures) > MAX_TRACKED:
            self._prune(now)

    def succeeded(self, key: str) -> None:
        self._failures.pop(key, None)
        self._locked_until.pop(key, None)

    def reset(self) -> None:
        self._failures.clear()
        self._locked_until.clear()

    def _prune(self, now: float) -> None:
        self._failures = {k: v for k, v in self._failures.items() if v and now - v[-1] < WINDOW_SECONDS}
        self._locked_until = {k: u for k, u in self._locked_until.items() if u > now}
