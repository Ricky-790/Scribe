import asyncio
from enum import StrEnum

from aiolimiter import AsyncLimiter
from pydantic_ai.exceptions import ModelHTTPError

from custom_logger import get_logger


class Provider(StrEnum):
    GOOGLE = "google"
    NVIDIA = "nvidia"


logger = get_logger()

# Shared across ALL Gemini calls in the pipeline
gemini_rate_limiter = AsyncLimiter(max_rate=10, time_period=60)

nvidia_rate_limiter = AsyncLimiter(max_rate=10, time_period=60)

_rate_limiters = {
    Provider.GOOGLE: gemini_rate_limiter,
    Provider.NVIDIA: nvidia_rate_limiter,
}


def extract_retry_delay(error: ModelHTTPError) -> float | None:
    try:
        details = error.body.get("error", {}).get("details", [])
        for d in details:
            if d.get("@type", "").endswith("RetryInfo"):
                return float(d.get("retryDelay", "").rstrip("s"))
    except Exception:
        pass
    return None


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
        except ModelHTTPError as e:  # Handle status_code 503 error
            last_error = e
            if e.status_code == 429 and attempt < max_retries - 1:
                wait = extract_retry_delay(e) or 45
                logger.warning(
                    f"[{provider}] Rate limited (attempt {attempt + 1}/{max_retries}),"
                    f" retrying in {wait:.0f}s"
                )
                await asyncio.sleep(wait)
                continue
            raise

    if last_error is not None:
        raise last_error
