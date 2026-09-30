import asyncio
import os
import random
from enum import StrEnum

from aiolimiter import AsyncLimiter
from pydantic_ai.exceptions import ModelHTTPError

from custom_logger import get_logger


class Provider(StrEnum):
    GOOGLE = "google"
    OPENROUTER = "openrouter"


logger = get_logger()

# Ceilings are per provider and process-wide. Research sub-agents run several
# requests each, so the OpenRouter allowance is sized for that fan-out while the
# Google bucket is held back for the consolidation stages, which have no
# alternative provider.
_GOOGLE_MAX_RATE = int(os.getenv("GOOGLE_RATE_LIMIT", "10"))
_OPENROUTER_MAX_RATE = int(os.getenv("OPENROUTER_RATE_LIMIT", "20"))

# Shared across ALL Gemini calls in the pipeline
gemini_rate_limiter = AsyncLimiter(max_rate=_GOOGLE_MAX_RATE, time_period=60)

openrouter_rate_limiter = AsyncLimiter(max_rate=_OPENROUTER_MAX_RATE, time_period=60)

_rate_limiters = {
    Provider.GOOGLE: gemini_rate_limiter,
    Provider.OPENROUTER: openrouter_rate_limiter,
}


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
    rate_limiter = _rate_limiters[provider]
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            async with rate_limiter:
                return await coro_fn(*args, **kwargs)
        except ModelHTTPError as e:
            if e.status_code not in RETRYABLE_STATUSES or attempt >= max_retries - 1:
                raise
            last_error = e
            wait = _backoff_delay(attempt, e.status_code, extract_retry_delay(e))
            logger.warning(
                f"[{provider}] {e.status_code} from provider "
                f"(attempt {attempt + 1}/{max_retries}), retrying in {wait:.1f}s"
            )
            await asyncio.sleep(wait)

    if last_error is not None:
        raise last_error
