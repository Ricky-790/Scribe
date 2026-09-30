"""
Single entry point the graph nodes use to invoke an agent.

Two problems are solved here, in one place, so no node has to know about them:

1. **Rate limiting and retries.** Each provider has its own bucket, and transient
   failures are retried with backoff. That used to be a `run_with_retry(...)` call
   sprinkled through every node, easy to forget.

2. **Provider fallback.** Quota and capacity limits are the common failure mode in
   this pipeline, and they are transient and provider-specific. When a step
   exhausts its retries on its primary provider, the orchestrator transparently
   retries that same step on the *other* provider with a fallback model. A step
   only fails when both providers fail, which is a genuinely different situation
   from "Gemini is busy right now".

The intent classifier is deliberately not routed through here: it runs before any
report exists, is a single call, and its result decides whether the pipeline runs
at all.
"""

import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider

from agents_service.pipeline.rate_limiting import Provider, run_with_retry
from custom_logger import get_logger

logger = get_logger()

T = TypeVar("T")

# Fallback models. Only used when a step's primary provider is exhausted, so they
# need to be broadly capable rather than tuned — several of these steps rely on
# tool calling and validated structured output.
FALLBACK_OPENROUTER_MODEL = os.getenv(
    "FALLBACK_OPENROUTER_MODEL", "google/gemini-2.5-flash"
)
FALLBACK_GOOGLE_MODEL = os.getenv("FALLBACK_GOOGLE_MODEL", "gemini-2.5-flash")


def build_model(model_name: str, provider: Provider):
    """Construct a pydantic-ai model for the given provider."""
    if provider is Provider.OPENROUTER:
        return OpenRouterModel(
            model_name,
            provider=OpenRouterProvider(api_key=os.getenv("OPENROUTER_API_KEY", "")),
        )
    return GoogleModel(
        model_name,
        provider=GoogleProvider(api_key=os.getenv("GOOGLE_API_KEY", "")),
    )


@dataclass(frozen=True)
class AgentStep:
    """
    One callable stage of the pipeline, with its provider strategy.

    ``build_agent`` is called per attempt rather than cached, so a fallback gets
    a genuinely fresh client pointed at the other provider instead of a mutated
    copy of the primary one.
    """

    name: str
    build_agent: Callable[[], Agent]
    provider: Provider
    # Overrides used when the primary provider cannot serve the step.
    fallback_provider: Provider | None = None
    fallback_build_agent: Callable[[], Agent] | None = None

    def resolve_fallback(self) -> tuple[Provider, Callable[[], Agent]] | None:
        if self.fallback_provider is None or self.fallback_build_agent is None:
            return None
        return self.fallback_provider, self.fallback_build_agent


class AgentOrchestrator:
    """
    Runs one pipeline step against its primary provider, then its fallback.

    Exposes a single method — ``run`` — which takes the step's callable. The
    callable receives the agent as its first argument, so the orchestrator stays
    agnostic about what each step actually does:

        result = await orchestrator.run(build_claims, store)

    ``fn`` must therefore be written as ``fn(agent, *args)``.
    """

    def __init__(self, step: AgentStep, max_retries: int = 4) -> None:
        self._step = step
        self._max_retries = max_retries

    @property
    def step_name(self) -> str:
        return self._step.name

    @property
    def provider(self) -> Provider:
        return self._step.provider

    async def run(
        self,
        fn: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Invoke ``fn(agent, *args)`` on the primary provider.

        Falls back to the alternate provider when the primary exhausts its
        retries. If the fallback also fails, that error propagates with the
        original attached, so a failure report shows what both providers did.
        """
        try:
            agent = self._step.build_agent()
            return await run_with_retry(
                fn,
                agent,
                *args,
                provider=self._step.provider,
                max_retries=self._max_retries,
                **kwargs,
            )
        except Exception as primary_error:
            fallback = self._step.resolve_fallback()
            if fallback is None:
                raise

            provider, build_agent = fallback
            logger.warning(
                f"[{self._step.name}] {self._step.provider.value} failed after "
                f"{self._max_retries} attempts "
                f"({type(primary_error).__name__}: {primary_error}); "
                f"falling back to {provider.value}"
            )

            try:
                agent = build_agent()
                return await run_with_retry(
                    fn,
                    agent,
                    *args,
                    provider=provider,
                    max_retries=self._max_retries,
                    **kwargs,
                )
            except Exception as fallback_error:
                logger.error(
                    f"[{self._step.name}] fallback to {provider.value} also failed: "
                    f"{type(fallback_error).__name__}: {fallback_error}"
                )
                raise fallback_error from primary_error


# ── Step registry ───────────────────────────────────────────────
#
# Imported lazily inside the function below so that this module can be imported
# from agent modules without a circular import.


def _steps() -> dict[str, AgentStep]:
    from agents_service.agents.challenge_agent import get_challenge_agent
    from agents_service.agents.claims_agent import get_claims_agent
    from agents_service.agents.decomposer_agent import get_decomposer_agent
    from agents_service.agents.diagram_agent import get_diagram_agent
    from agents_service.agents.replan_agent import get_replan_agent
    from agents_service.agents.subagent import get_subagent
    from agents_service.agents.synthesizer_agent import (
        get_outline_agent,
        get_section_writer_agent,
    )

    def with_fallback(
        name: str,
        provider: Provider,
        build: Callable[..., Agent],
        **factory_kwargs: Any,
    ) -> AgentStep:
        """Pair a Google-primary step with its OpenRouter mirror, or vice versa."""
        if provider is Provider.OPENROUTER:
            fallback_provider = Provider.GOOGLE
            fallback_model = FALLBACK_GOOGLE_MODEL
        else:
            fallback_provider = Provider.OPENROUTER
            fallback_model = FALLBACK_OPENROUTER_MODEL

        return AgentStep(
            name=name,
            build_agent=lambda: build(provider=provider, **factory_kwargs),
            provider=provider,
            fallback_provider=fallback_provider,
            fallback_build_agent=lambda: build(
                provider=fallback_provider, model_name=fallback_model, **factory_kwargs
            ),
        )

    return {
        step.name: step
        for step in (
            with_fallback("plan", Provider.GOOGLE, get_decomposer_agent),
            with_fallback("research", Provider.OPENROUTER, get_subagent),
            with_fallback("build_claims", Provider.GOOGLE, get_claims_agent),
            with_fallback("challenge", Provider.GOOGLE, get_challenge_agent),
            with_fallback("replan", Provider.GOOGLE, get_replan_agent),
            with_fallback("outline", Provider.GOOGLE, get_outline_agent),
            with_fallback("write_section", Provider.GOOGLE, get_section_writer_agent),
            with_fallback("diagram", Provider.OPENROUTER, get_diagram_agent),
        )
    }


_STEP_CACHE: dict[str, AgentStep] | None = None


def get_orchestrator(step_name: str) -> AgentOrchestrator:
    """Return the orchestrator for a named step."""
    global _STEP_CACHE
    if _STEP_CACHE is None:
        _STEP_CACHE = _steps()
    try:
        return AgentOrchestrator(_STEP_CACHE[step_name])
    except KeyError:
        raise KeyError(
            f"Unknown pipeline step '{step_name}'. "
            f"Known steps: {sorted(_STEP_CACHE)}"
        ) from None
