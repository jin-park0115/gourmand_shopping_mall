"""로그인 연속 실패 잠금: 같은 이메일 10분 안 5번 실패 → 10분 동안 429."""
import pytest
from httpx import ASGITransport, AsyncClient

from database import get_session
from domain.auth.login_guard import LOCK_SECONDS, MAX_FAILURES, WINDOW_SECONDS, LoginGuard
from domain.exceptions import TooManyRequestsError
from main import app


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _fail(guard: LoginGuard, key: str, times: int) -> None:
    for _ in range(times):
        guard.check(key)
        guard.failed(key)


def test_locks_after_max_failures_and_unlocks_later() -> None:
    clock = FakeClock()
    guard = LoginGuard(clock)
    _fail(guard, "kim@test.com", MAX_FAILURES - 1)
    guard.check("kim@test.com")  # 4번까지는 괜찮아요
    guard.failed("kim@test.com")  # 5번째
    with pytest.raises(TooManyRequestsError, match="10분 뒤"):
        guard.check("kim@test.com")
    clock.now += LOCK_SECONDS - 61
    with pytest.raises(TooManyRequestsError, match="2분 뒤"):
        guard.check("kim@test.com")
    clock.now += 61
    guard.check("kim@test.com")  # 풀렸어요


def test_old_failures_do_not_count() -> None:
    clock = FakeClock()
    guard = LoginGuard(clock)
    _fail(guard, "kim@test.com", MAX_FAILURES - 1)
    clock.now += WINDOW_SECONDS  # 10분이 지나면 이전 실패는 안 세요
    _fail(guard, "kim@test.com", MAX_FAILURES - 1)
    guard.check("kim@test.com")


def test_success_resets_and_keys_are_separate() -> None:
    guard = LoginGuard(FakeClock())
    _fail(guard, "kim@test.com", MAX_FAILURES - 1)
    guard.succeeded("kim@test.com")
    _fail(guard, "kim@test.com", MAX_FAILURES - 1)
    guard.check("kim@test.com")
    _fail(guard, "lee@test.com", MAX_FAILURES)
    with pytest.raises(TooManyRequestsError):
        guard.check("lee@test.com")
    guard.check("kim@test.com")  # 다른 이메일은 상관없어요


def test_memory_is_pruned() -> None:
    clock = FakeClock()
    guard = LoginGuard(clock)
    guard.failed("old@test.com")
    clock.now += WINDOW_SECONDS
    for i in range(10_001):
        guard.failed(f"user{i}@test.com")
    assert "old@test.com" not in guard._failures


# ── API ──

PASSWORD = "secret-123"


@pytest.fixture
async def client(db_session):
    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _login(client, email: str, password: str):
    return await client.post("/auth/login", data={"username": email, "password": password})


@pytest.mark.anyio
async def test_login_is_locked_after_five_failures(client) -> None:
    for email in ("kim@test.com", "lee@test.com"):
        await client.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": "회원"})

    for _ in range(MAX_FAILURES):
        assert (await _login(client, "kim@test.com", "wrong-pass")).status_code == 401

    res = await _login(client, "KIM@test.com", PASSWORD)  # 맞는 비밀번호 · 대소문자 달라도 같은 계정
    assert res.status_code == 429
    assert res.json()["code"] == "TOO_MANY_REQUESTS" and "10분 뒤" in res.json()["message"]
    assert (await _login(client, "lee@test.com", PASSWORD)).status_code == 200  # 다른 계정은 그대로


@pytest.mark.anyio
async def test_unknown_email_is_counted_too(client) -> None:
    for _ in range(MAX_FAILURES):
        assert (await _login(client, "nobody@test.com", "x")).status_code == 401
    assert (await _login(client, "nobody@test.com", "x")).status_code == 429


@pytest.mark.anyio
async def test_success_clears_failures(client) -> None:
    await client.post("/auth/signup", json={"email": "kim@test.com", "password": PASSWORD, "name": "회원"})
    for _ in range(MAX_FAILURES - 1):
        await _login(client, "kim@test.com", "wrong-pass")
    assert (await _login(client, "kim@test.com", PASSWORD)).status_code == 200
    for _ in range(MAX_FAILURES - 1):
        assert (await _login(client, "kim@test.com", "wrong-pass")).status_code == 401
