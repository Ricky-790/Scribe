"""
Manual test harness for the research pipeline.

Runs the full LangGraph pipeline on a topic and writes the finished report to
Markdown. This exercises the real agents — a live LLM for every stage and real
web search for each research task — so it needs working API keys in .env.

    python main.py "your research question"
    python main.py "your question" --output report.md
    python main.py "your question" --categories finance,technology --no-diagrams
    python main.py "your question" --save-claims

Nothing here touches Postgres or Celery: the report id is generated locally and
diagram uploads are skipped unless Supabase is configured.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

from agents_service.agents.classifier_agent import (  # noqa: E402
    classify_query,
    get_classifier_agent,
)
from agents_service.graph.graph import MAX_REPLAN_ROUNDS, get_research_graph  # noqa: E402
from agents_service.pipeline.rate_limiting import release_resources  # noqa: E402
from agents_service.models import IntentEnum  # noqa: E402

# ── Console ──────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def _supports_colour() -> bool:
    return sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def _c(text: str, colour: str) -> str:
    return f"{colour}{text}{RESET}" if _supports_colour() else text


def header(text: str) -> None:
    print()
    print(_c(text, BOLD))
    print(_c("─" * len(text), DIM))


def info(text: str) -> None:
    print(f"  {text}")


def success(text: str) -> None:
    print(f"  {_c('✓', GREEN)} {text}")


def warn(text: str) -> None:
    print(f"  {_c('!', YELLOW)} {text}")


def fail(text: str) -> None:
    print(f"  {_c('✗', RED)} {text}")


def event_line(data: dict) -> str:
    """Render one pipeline event as a single readable line."""
    phase = data.get("phase", "?")
    status = data.get("status", "")
    parts = [_c(f"[{phase}]", CYAN)]

    if data.get("task_name"):
        parts.append(data["task_name"])
    if data.get("msg"):
        parts.append(data["msg"])
    elif data.get("status"):
        parts.append(status)
    return " ".join(str(p) for p in parts if p)


# ── Pipeline ─────────────────────────────────────────────────────


async def classify(topic: str, skip: bool) -> tuple[list[str], str | None]:
    """
    Resolve categories for the topic.

    The classifier is a live LLM call, so a test run that only cares about the
    pipeline can skip it and pass --categories instead.
    """
    if skip:
        warn("Skipping classification; using the supplied/default categories.")
        return [], None

    header("Classifying")
    try:
        result = await classify_query(topic, get_classifier_agent())
    except Exception as exc:
        warn(f"Classification failed ({type(exc).__name__}: {exc})")
        warn("Falling back to no categories — the planner will work without them.")
        return [], None

    categories = [c.value for c in result.categories]
    info(f"intent:     {result.intent.value}")
    info(f"categories: {', '.join(categories) or '(none)'}")

    if result.intent != IntentEnum.RESEARCH_TOPIC:
        warn(
            f"Classifier judged this '{result.intent.value}', not a research topic. "
            f"Continuing anyway."
        )
    return categories, result.response


def suppress_diagrams() -> None:
    """
    Make every diagram attempt fail fast, so the run writes prose instead.

    Diagram generation runs real E2B sandboxes and uploads to Supabase, which is
    slow and costs money. `--no-diagrams` swaps the executor for one that raises
    immediately: the graph already treats a diagram failure as non-fatal and
    asks the section writer to describe the idea in prose, so the report still
    comes out complete.

    This is patched in the harness rather than added to the graph so the
    production pipeline keeps no test-only branches.
    """
    import agents_service.graph.nodes as nodes

    def _disabled(*_args, **_kwargs):
        raise RuntimeError("diagram generation disabled by --no-diagrams")

    nodes.execute_diagram = _disabled


async def run_pipeline(
    topic: str,
    categories: list[str],
    report_id: str,
) -> dict | None:
    """Drive the graph to completion, echoing events as they stream."""
    graph = get_research_graph()

    initial_state = {
        "report_id": report_id,
        "query": topic,
        "categories": categories,
        "plan": None,
        "replan_tasks": [],
        "replan_count": 0,
        "task_results": {},
        "claim_graph": None,
        "challenge_result": None,
        "replan_plan": None,
        "report_outline": None,
        "written_sections": {},
        "final_report": None,
        "error": None,
    }

    started = time.monotonic()
    final_state: dict = {}
    task_events: list[tuple[str, str, str]] = []

    try:
        async for event in graph.astream(
            initial_state,
            stream_mode=["custom", "values"],
            version="v2",
            subgraphs=True,
        ):
            if event.get("type") == "custom":
                data = event.get("data") or {}
                info(event_line(data))
                if data.get("task_id"):
                    task_events.append(
                        (
                            str(data.get("task_id")),
                            str(data.get("task_name", "")),
                            str(data.get("task_status", "")),
                        )
                    )
            elif event.get("type") == "values":
                state = event.get("data")
                if isinstance(state, dict):
                    final_state = state
    except Exception as exc:
        fail(f"Pipeline raised {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()
        return None

    final_state["_elapsed"] = time.monotonic() - started
    final_state["_task_events"] = task_events
    return final_state


def summarise(final_state: dict, disable_diagrams: bool) -> None:
    """Report what the run actually produced."""
    header("Run summary")

    results = final_state.get("task_results") or {}
    if results:
        by_status: dict[str, int] = {}
        for result in results.values():
            key = str(getattr(result.status, "value", result.status))
            by_status[key] = by_status.get(key, 0) + 1
        detail = ", ".join(f"{n} {s}" for s, n in sorted(by_status.items()))
        info(f"tasks run:    {len(results)} ({detail})")

        # Name the failures: a count alone hides which topic went unanswered,
        # and whether it was retried or died on the first attempt.
        failed = [
            r for r in results.values()
            if str(getattr(r.status, "value", r.status)) == "failed"
        ]
        for result in failed:
            names = [n for t, n in final_state.get("_task_events", []) if t == result.task_id]
            label = names[-1] if names else result.task_id
            info(f"  {_c('failed:', RED)} {result.task_id} — {label}")

    claim_graph = final_state.get("claim_graph")
    if claim_graph and claim_graph.claims:
        conflicting = [
            c for c in claim_graph.claims if str(c.status) == "conflicting"
        ]
        unsupported = [c for c in claim_graph.claims if str(c.status) == "unsupported"]
        info(f"claims built: {len(claim_graph.claims)}")
        if conflicting:
            info(f"  conflicting: {len(conflicting)}")
        if unsupported:
            info(f"  unsupported: {len(unsupported)}")

        used: set[str] = set()
        for claim in claim_graph.claims:
            used.update(claim.supporting_tasks)
        contributing = {
            task_id
            for task_id, result in results.items()
            if str(getattr(result.status, "value", result.status)) != "failed"
        }
        if contributing:
            pct = (len(contributing & used) / len(contributing)) * 100
            info(f"  task coverage: {len(contributing & used)}/{len(contributing)} ({pct:.0f}%)")

    challenge = final_state.get("challenge_result")
    if challenge:
        if challenge.status == "sufficient":
            success(f"challenge:    sufficient — no issues found")
        else:
            info(f"challenge:    {len(challenge.issues)} issue(s) found")
            for issue in challenge.issues:
                info(f"  {_c(issue.claim_id, YELLOW)}: {issue.problem}")

    rounds = final_state.get("replan_count", 0)
    info(f"replan rounds: {rounds} (cap {MAX_REPLAN_ROUNDS})")

    outline = final_state.get("report_outline")
    if outline:
        info(f"sections:     {len(outline.sections)}")
        for section in sorted(outline.sections, key=lambda s: s.order):
            claims = ",".join(section.relevant_claim_ids) or "—"
            info(f"  {section.order}. {section.title}  {_c(f'[{claims}]', DIM)}")

    if not disable_diagrams:
        diagrams = [
            d
            for section in (outline.sections if outline else [])
            for d in section.diagrams
        ]
        rendered = sum(1 for d in diagrams if d.url)
        if diagrams:
            info(f"diagrams:     {rendered}/{len(diagrams)} rendered")

    info(f"elapsed:      {final_state.get('_elapsed', 0):.1f}s")


def write_report(report, path: Path) -> None:
    path.write_text(report.content, encoding="utf-8")
    words = len(report.content.split())
    mins = max(1, round(words / 220))
    success(f"Wrote {path} ({words} words, ~{mins} min read)")


def write_claims(final_state: dict, path: Path) -> None:
    """Dump the claim graph for inspection."""
    claim_graph = final_state.get("claim_graph")
    if claim_graph is None:
        warn("No claim graph was built.")
        return
    path.write_text(claim_graph.model_dump_json(indent=2), encoding="utf-8")
    success(f"Wrote {path} ({len(claim_graph.claims)} claims)")


# ── Entry point ──────────────────────────────────────────────────


async def run(topic: str, args: argparse.Namespace) -> int:
    report_id = args.report_id or str(uuid4())

    header("Topic")
    info(topic)
    info(f"report id: {report_id}")

    categories, _ = await classify(topic, args.skip_classifier)
    if args.categories:
        categories = args.categories
        info(f"using categories: {', '.join(categories)}")

    if args.no_diagrams:
        warn("Diagrams disabled (--no-diagrams) — sections will describe visuals in prose.")
        suppress_diagrams()
    elif not os.getenv("SUPABASE_BUCKET_ID"):
        warn("SUPABASE_BUCKET_ID is unset, so any diagram will fall back to prose.")

    header("Pipeline")
    info("plan → research → build claims → challenge → [replan] → synthesis")
    print()

    try:
        final_state = await run_pipeline(topic, categories, report_id)
    finally:
        # Close the rate limiter's Redis pool, which is bound to this loop.
        await release_resources()

    if final_state is None:
        return 1

    summarise(final_state, args.no_diagrams)

    header("Output")
    report = final_state.get("final_report")
    if report is None:
        fail("The pipeline finished without producing a report.")
        fail("Check the log above — usually the research tasks all failed.")
        if args.save_claims:
            write_claims(final_state, Path(args.claims_out))
        return 1

    write_report(report, Path(args.output))
    if args.save_claims:
        write_claims(final_state, Path(args.claims_out))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the research pipeline on a topic and save the report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("topic", help="The research question to investigate.")
    parser.add_argument(
        "-o", "--output", default="test.md", help="Where to write the report."
    )
    parser.add_argument(
        "-c",
        "--categories",
        nargs="+",
        help="Skip the classifier and use these categories.",
    )
    parser.add_argument(
        "--skip-classifier",
        action="store_true",
        help="Skip the classifier call and plan without categories.",
    )
    parser.add_argument(
        "--no-diagrams",
        action="store_true",
        help="Suppress diagram generation (faster; no E2B sandbox or uploads).",
    )
    parser.add_argument(
        "--save-claims",
        action="store_true",
        help="Also write the claim graph as JSON.",
    )
    parser.add_argument(
        "--claims-out", default="claims.json", help="Where to write the claim graph."
    )
    parser.add_argument(
        "--report-id", help="Use a fixed report id (defaults to a random UUID)."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not os.getenv("GOOGLE_API_KEY"):
        print(
            f"{_c('✗', RED)} GOOGLE_API_KEY is not set. Copy .env.example to .env and "
            f"fill in your keys."
        )
        return 2
    if not args.no_diagrams and not os.getenv("TAVILY_API_KEY"):
        print(
            f"{_c('!', YELLOW)} TAVILY_API_KEY is not set — every research task will "
            f"fail to find sources."
        )

    try:
        return asyncio.run(run(args.topic, args))
    except KeyboardInterrupt:
        print(f"\n{_c('Interrupted.', YELLOW)}")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
