import asyncio
import os
import random
import time
import weakref
from dataclasses import dataclass
from enum import StrEnum

import redis.asyncio as aioredis
from limits import parse
from limits.aio.storage import RedisStorage
from limits.aio.strategies import SlidingWindowCounterRateLimiter
from limits.util import RateLimitItem
from pydantic_ai.exceptions import ModelHTTPError

from custom_logger import get_logger


class Provider(StrEnum):
    GOOGLE = "google"
    OPENROUTER = "openrouter"


class RateLimitTimeout(Exception):
    """
    Raised when a provider's shared budget did not free up in time.

    Distinct from a provider error: the provider may be perfectly healthy, we
    simply could not get a slot. The orchestrator treats it like exhaustion and
    tries the other provider.
    """


logger = get_logger()

# Per-provider global budgets, shared by every worker via Redis. Google and
# OpenRouter have independent quotas, so they get independent keys — a shared
# counter would let OpenRouter traffic exhaust the Gemini allowance.
_GOOGLE_MAX_RATE = int(os.getenv("GOOGLE_RATE_LIMIT", "10"))
_OPENROUTER_MAX_RATE = int(os.getenv("OPENROUTER_RATE_LIMIT", "20"))

_REDIS_URL = os.getenv("REDIS_RATE_LIMIT_URL") or os.getenv(
    "REDIS_BROKER_URL", "redis://localhost:6379/0"
)
_KEY_PREFIX = os.getenv("RATE_LIMIT_KEY_PREFIX", "SCRIBE")

# How long to queue for a slot before giving up and letting the caller fall back
# to the other provider. Long enough to ride out a busy window, short enough that
# a genuinely saturated provider does not stall the whole report.
_WAIT_CEILING_SECONDS = float(os.getenv("RATE_LIMIT_WAIT_SECONDS", "30"))
_POLL_INTERVAL_SECONDS = 0.25

# Per-loop limiter cache.
#
# Keyed by event loop on purpose: Celery runs each task under a fresh
# asyncio.run(), and a pooled connection holds a transport bound to the loop
# that opened it. A shared pool hands that stale connection to the next loop and
# fails with "Event loop is closed" — intermittently, since the pool may or may
# not have a connection cached when the new loop asks for one. Verified against
# limits 5.8.0 + redis-py 6.4.0.
_POOLS: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, aioredis.ConnectionPool]" = (
    weakref.WeakKeyDictionary()
)
_LIMITERS: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[Provider, SlidingWindowCounterRateLimiter]]" = (
    weakref.WeakKeyDictionary()
)
_ITEMS: dict[Provider, RateLimitItem] = {
    Provider.GOOGLE: parse(f"{_GOOGLE_MAX_RATE}/minute"),
    Provider.OPENROUTER: parse(f"{_OPENROUTER_MAX_RATE}/minute"),
}

# Emitted once per process, not once per skipped check, so an outage does not
# drown the log.
_warned_unavailable: set[str] = set()


@dataclass
class _LoopResources:
    pool: aioredis.ConnectionPool
    storage: RedisStorage
    limiters: dict[Provider, SlidingWindowCounterRateLimiter]


_resources: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, _LoopResources]" = (
    weakref.WeakKeyDictionary()
)


def _get_resources() -> _LoopResources:
    """Limiter set for the running loop, creating it on first use."""
    loop = asyncio.get_running_loop()
    existing = _resources.get(loop)
    if existing is not None:
        return existing

    pool = aioredis.ConnectionPool.from_url(
        _REDIS_URL, max_connections=int(os.getenv("RATE_LIMIT_POOL_SIZE", "8"))
    )
    # implementation="redispy" is required: the default is "coredis", whose
    # fixed-window INCR + EXPIRE is two round trips and can leave a key with no
    # TTL, which would then reject that provider forever (limits issue #371).
    storage = RedisStorage(
        f"async+{_REDIS_URL}",
        implementation="redispy",
        key_prefix=_KEY_PREFIX,
        connection_pool=pool,
    )
    limiters = {
        provider: SlidingWindowCounterRateLimiter(storage)
        for provider in Provider
    }
    created = _LoopResources(pool=pool, storage=storage, limiters=limiters)
    _resources[loop] = created
    return created


async def release_resources() -> None:
    """Close this loop's Redis pool. Called when a pipeline run finishes."""
    loop = asyncio.get_running_loop()
    existing = _resources.pop(loop, None)
    if existing is None:
        return
    try:
        await existing.pool.aclose()
    except Exception:
        logger.debug("Failed to close rate-limit pool cleanly", exc_info=True)


async def _try_hit(provider: Provider) -> bool:
    limiter = _get_resources().limiters[provider]
    return await limiter.hit(_ITEMS[provider], "requests")


async def acquire_slot(provider: Provider) -> None:
    """
    Block until this provider's global budget allows one request.

    Fails open: if Redis is unreachable the request proceeds unthrottled. Redis
    is also the Celery broker, so it being down means no tasks are being
    dispatched at all; refusing here would stall every in-flight report for a
    dependency the pipeline cannot function without anyway.
    """
    deadline = time.monotonic() + _WAIT_CEILING_SECONDS

    try:
        while True:
            if await _try_hit(provider):
                return
            if time.monotonic() >= deadline:
                raise RateLimitTimeout(
                    f"No {provider.value} request slot available within "
                    f"{_WAIT_CEILING_SECONDS:.0f}s "
                    f"({_GOOGLE_MAX_RATE if provider is Provider.GOOGLE else _OPENROUTER_MAX_RATE}"
                    f"/min shared across workers)."
                )
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    except RateLimitTimeout:
        raise
    except Exception as exc:
        if "redis" not in str(exc).lower() and not isinstance(
            exc, (aioredis.RedisError, OSError)
        ):
            raise
        if provider.value not in _warned_unavailable:
            _warned_unavailable.add(provider.value)
            logger.warning(
                f"[{provider.value}] Redis rate limiter unavailable ({exc}); "
                f"proceeding unthrottled."
            )
        return


def extract_retry_delay(error: ModelHTTPError) -> float | None:
    """
    Pull a provider-suggested retry delay out of an error body, if there is one.

    Google returns a RetryInfo detail carrying a retryDelay; OpenRouter sends a
    plain message without one. Returning None in that case is fine — the caller
    falls back to its own default backoff.
    """
    try:
        body = error.body or {}
        payload = body.get("error", body)
        for detail in payload.get("details", []) or []:
            if str(detail.get("@type", "")).endswith("RetryInfo"):
                delay = str(detail.get("retryDelay", "")).rstrip("s")
                if delay:
                    return float(delay)

        # OpenRouter sometimes spells the wait out in the message.
        message = str(payload.get("message", ""))
        for marker in ("retry after", "try again in"):
            if marker in message.lower():
                tail = message.lower().split(marker, 1)[1]
                digits = "".join(
                    ch for ch in tail[:8] if ch.isdigit() or ch == "."
                )
                if digits:
                    return float(digits.rstrip("."))
    except Exception:
        pass
    return None


# Statuses worth retrying: 429 is a quota/rate limit, and 5xx from the
# provider is transient (overload, internal error). Both clear on their own.
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _backoff_delay(attempt: int, status_code: int, retry_after: float | None) -> float:
    """
    Wait before the next attempt.

    A 429 uses the provider's own Retry-After when it supplies one, otherwise
    the default. Transient server errors back off exponentially with jitter —
    retrying them all at the same instant just reproduces the overload.
    """
    if retry_after:
        return retry_after
    if status_code == 429:
        return 45.0
    return min(2.0 * (2**attempt) + random.uniform(0, 1.5), 30.0)


async def run_with_retry(
    coro_fn,
    *args,
    max_retries: int = 4,
    provider: Provider = Provider.GOOGLE,
    **kwargs,
):
    """
    Run an agent call, spending one shared budget slot per attempt.

    Each attempt acquires its own slot. Wrapping the whole loop in a single
    slot would let a retry fire immediately after the original and double-count
    against the provider's quota.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            await acquire_slot(provider)
            return await coro_fn(*args, **kwargs)
        except (ModelHTTPError, RateLimitTimeout) as e:
            status_code = getattr(e, "status_code", None)
            retryable = isinstance(e, RateLimitTimeout) or status_code in RETRYABLE_STATUSES
            if not retryable or attempt >= max_retries - 1:
                raise
            last_error = e
            if isinstance(e, RateLimitTimeout):
                wait = 1.0
            else:
                wait = _backoff_delay(attempt, status_code, extract_retry_delay(e))
            logger.warning(
                f"[{provider.value}] "
                + (
                    "shared budget exhausted"
                    if isinstance(e, RateLimitTimeout)
                    else f"{status_code} from provider"
                )
                + f" (attempt {attempt + 1}/{max_retries}), retrying in {wait:.1f}s"
            )
            await asyncio.sleep(wait)

    if last_error is not None:
        raise last_error