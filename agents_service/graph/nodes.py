import asyncio
import os
import re
import weakref
from uuid import uuid4

from langgraph.types import StreamWriter

from agents_service.agents import (
    build_claims,
    challenge_claims,
    create_replan,
    create_research_plan,
    execute_task,
    generate_outline,
    write_section,
)
from agents_service.agents.synthesizer_agent import enrich_outline_with_diagrams
from agents_service.graph.state import (
    ResearchGraphState,
    SectionWriteState,
    TaskExecutionState,
)
from agents_service.models import (
    ClaimGraph,
    Report,
    ReportSection,
    Task,
    TaskResult,
    TaskResultStatus,
)
from agents_service.models.synthesizer_models import GeneratedDiagram
from agents_service.pipeline.diagram_executor import execute_diagram
from agents_service.pipeline.orchestrator import get_orchestrator
from agents_service.pipeline.storage import upload_to_bucket
from agents_service.tools.store import ResearchStore
from custom_logger import get_logger

logger = get_logger()

_UNSAFE_KEY_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_object_name(name: str) -> str:
    """
    Reduce a diagram filename to a storage-key-safe stem.

    The chart branch's filename is chosen by the model, so it can contain
    spaces or parentheses — which would truncate the `supabase::` placeholder
    at the first `)` and permanently break the image in the rendered report.
    """
    stem = _UNSAFE_KEY_CHARS.sub("_", name).strip("._-")
    return stem or "diagram"


def _store_for(state: ResearchGraphState) -> ResearchStore:
    return ResearchStore(
        question=state["query"],
        task_results=state.get("task_results", {}),
        claim_graph=state.get("claim_graph"),
    )


# ─── Node: Decompose (Graph Entry Point) ─────────────────────────


async def decompose_node(state: ResearchGraphState, writer: StreamWriter) -> dict:
    """Generate the initial research plan. This is the graph entry point."""
    writer({"phase": "planning", "status": "starting"})

    plan = await get_orchestrator("plan").run(
        create_research_plan, state["query"], state["categories"]
    )
    logger.info(f"Plan generated with {len(plan.tasks)} tasks")

    writer(
        {
            "phase": "planning",
            "status": "finished",
            "strategy": plan.strategy_summary,
            "msg": f"Research plan summary: {plan.strategy_summary}",
            "plan": plan,
        }
    )

    return {"plan": plan, "replan_count": 0, "replan_tasks": []}


# ─── Node: Re-enter research after a replan ───────────────────────


async def plan_research_node(state: ResearchGraphState, writer: StreamWriter) -> dict:
    """Announce a correction round before its tasks fan out."""
    round_number = state.get("replan_count", 0) + 1
    task_count = len(state.get("replan_tasks", []))

    writer(
        {
            "phase": "researching",
            "status": "starting",
            "msg": f"Round {round_number}: running {task_count} follow-up "
            f"task{'s' if task_count != 1 else ''}.",
        }
    )
    return {}


# ─── Node: Execute a single research task ─────────────────────────


# Research sub-agents are the most expensive and most quota-hungry calls in the
# pipeline. LangGraph dispatches one Send per task at once, so without a gate a
# five-task plan puts five agents in flight simultaneously and they exhaust the
# provider allowance against each other. Capping in-flight agents keeps the
# fan-out wide enough to be fast without starving the tasks that are running.
MAX_PARALLEL_SUBAGENTS = int(os.getenv("MAX_PARALLEL_SUBAGENTS", "3"))

# Keyed by event loop on purpose: Celery gives each task a fresh loop via
# asyncio.run, and a semaphore captured on a dead loop would deadlock.
_subagent_gates: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = (
    weakref.WeakKeyDictionary()
)


def _subagent_gate() -> asyncio.Semaphore:
    """Return the semaphore governing sub-agent concurrency on this event loop."""
    loop = asyncio.get_running_loop()
    gate = _subagent_gates.get(loop)
    if gate is None:
        gate = asyncio.Semaphore(MAX_PARALLEL_SUBAGENTS)
        _subagent_gates[loop] = gate
    return gate


async def execute_task_node(state: TaskExecutionState, writer: StreamWriter) -> dict:
    """
    Runs one research task. Invoked via Send, so `state` is the payload the
    conditional edge built rather than the graph state.
    """
    task = state["task"]

    logger.info(f"Starting task {task.id}: {task.name}")
    writer(
        {
            "phase": "researching",
            "status": "running",
            "task_id": task.id,
            "task_name": task.name,
            "task_status": "running",
        }
    )

    try:
        # Queued behind the in-flight cap. The agent is built by the
        # orchestrator inside the gate so waiting tasks do not each construct a
        # model client up front.
        async with _subagent_gate():
            result = await get_orchestrator("research").run(
                execute_task,
                task,
                state.get("prior_claims") or None,
                state.get("known_problems") or None,
            )
        logger.info(f"Task {task.id} finished with status={result.status}")
        writer(
            {
                "phase": "researching",
                "status": "running",
                "task_id": task.id,
                "task_name": task.name,
                "task_status": "done",
                "task_result": result.model_dump_json(),
            }
        )
    except Exception:
        # One failed task must not sink the run: its claim is simply absent, and
        # the challenge stage can flag the resulting coverage gap.
        logger.exception(f"Task {task.id} failed after retries")
        result = TaskResult(
            task_id=task.id,
            status=TaskResultStatus.FAILED,
            claim=f"This task could not be completed; no finding was established "
            f"for: {task.objective}",
            supporting_points=[],
            sources=[],
        )
        writer(
            {
                "phase": "researching",
                "status": "running",
                "task_id": task.id,
                "task_name": task.name,
                "task_status": "failed",
                "task_result": result.model_dump_json(),
            }
        )

    return {"task_results": {task.id: result}}


# ─── Node: Build the claim graph ──────────────────────────────────


def _log_claim_coverage(claim_graph: ClaimGraph, store: ResearchStore) -> None:
    """
    Warn when the research was only partly used.

    A tool-driven agent can stop early and return a graph that looks fine while
    silently dropping tasks. Coverage is checked rather than enforced, because a
    task that genuinely yielded nothing is legitimate — but a low ratio is
    worth seeing in the logs either way.
    """
    contributing = set(store.contributing_task_ids())
    if not contributing:
        return

    used: set[str] = set()
    for claim in claim_graph.claims:
        used.update(claim.supporting_tasks)
        used.update(e.task_id for e in claim.evidence)

    missing = contributing - used
    ratio = (len(contributing) - len(missing)) / len(contributing)
    logger.info(
        f"Claim coverage: {len(contributing) - len(missing)}/{len(contributing)} "
        f"tasks represented ({ratio:.0%})"
    )
    if missing:
        logger.warning(
            f"{len(missing)} task(s) produced findings but appear in no claim: "
            f"{sorted(missing)}"
        )


async def build_claims_node(state: ResearchGraphState, writer: StreamWriter) -> dict:
    """
    Consolidate every task result into the canonical claim graph.

    Runs after every research round, over the accumulated results, so a replan
    round re-consolidates from scratch rather than patching the previous graph.
    """
    store = _store_for(state)
    total = len(store.task_results)
    done = len(store.contributing_task_ids())

    writer(
        {
            "phase": "verifying",
            "status": "running",
            "msg": f"Consolidating {done} finding{'s' if done != 1 else ''} "
            f"into claims.",
        }
    )

    if done == 0:
        logger.warning("No task produced a finding; skipping claim consolidation")
        return {"claim_graph": ClaimGraph(claims=[]), "challenge_result": None}

    claim_graph = await get_orchestrator("build_claims").run(build_claims, store)

    writer(
        {
            "phase": "verifying",
            "status": "running",
            "msg": f"Built {len(claim_graph.claims)} claims from {done} of "
            f"{total} tasks.",
        }
    )
    _log_claim_coverage(claim_graph, store)

    return {"claim_graph": claim_graph}


# ─── Node: Challenge the claim graph ──────────────────────────────


async def challenge_node(state: ResearchGraphState, writer: StreamWriter) -> dict:
    """Interrogate the claim graph; the result decides loop vs. synthesis."""
    store = _store_for(state)
    claim_graph = state.get("claim_graph")

    if claim_graph is None or not claim_graph.claims:
        logger.warning("No claim graph to challenge; proceeding to synthesis")
        return {"challenge_result": None}

    writer(
        {
            "phase": "verifying",
            "status": "running",
            "msg": f"Checking {len(claim_graph.claims)} claims for support and coverage.",
        }
    )

    challenge = await get_orchestrator("challenge").run(
        challenge_claims, store.with_claims(claim_graph)
    )

    if challenge.status == "needs_research":
        writer(
            {
                "phase": "verifying",
                "status": "running",
                "msg": f"Found {len(challenge.issues)} issue(s) to research.",
            }
        )
    else:
        writer(
            {
                "phase": "verifying",
                "status": "finished",
                "msg": "All claims check out.",
            }
        )

    return {"challenge_result": challenge}


# ─── Node: Replan ─────────────────────────────────────────────────


async def replan_node(state: ResearchGraphState, writer: StreamWriter) -> dict:
    """Turn the challenge stage's issues into the next round of tasks."""
    store = _store_for(state)
    challenge = state.get("challenge_result")

    if challenge is None or not challenge.issues:
        logger.info("Replan requested with no issues recorded; nothing to do")
        return {"replan_plan": None}

    round_number = state.get("replan_count", 0) + 1
    replan = await get_orchestrator("replan").run(
        create_replan, store, challenge, round_number
    )

    if not replan.tasks:
        logger.warning("Replan produced no tasks; stopping the correction loop")
        writer(
            {
                "phase": "verifying",
                "status": "running",
                "msg": "No follow-up research could be planned.",
            }
        )
        return {"replan_plan": None}

    # Reuse the Task schema so replan tasks flow through the same fan-out and
    # persistence path as the original plan.
    tasks = [
        Task(
            id=task.task_id,
            name=task.name,
            objective=task.objective,
            evidence_requirements=task.evidence_requirements,
        )
        for task in replan.tasks
    ]

    writer(
        {
            "phase": "verifying",
            "status": "running",
            "msg": f"Planning {len(tasks)} follow-up task(s).",
            # The worker persists these so the run's task list reflects what the
            # review stage asked for, not just the original plan.
            "replan_tasks": [task.model_dump(mode="json") for task in tasks],
        }
    )

    return {"replan_plan": replan, "replan_tasks": tasks, "replan_count": round_number}


# ─── Node: Generate Outline ───────────────────────────────────────


async def synthesize_outline_node(
    state: ResearchGraphState, writer: StreamWriter
) -> dict:
    """Creates the report outline from the canonical claims."""
    claim_graph = state.get("claim_graph")

    if claim_graph is None:
        return {}

    writer({"phase": "synthesis", "status": "starting"})

    outline = await get_orchestrator("outline").run(
        generate_outline,
        state["query"],
        claim_graph,
        state["task_results"],
    )
    logger.info(f"Outline generated with {len(outline.sections)} sections")

    writer(
        {
            "phase": "synthesis",
            "status": "running",
            "msg": "Report outline generated",
        }
    )

    return {"report_outline": outline}


# ─── Generate Diagram ─────────────────────────────────────────────


async def generate_diagrams_node(
    state: ResearchGraphState, writer: StreamWriter
) -> dict:
    outline = state["report_outline"]

    sections_with_diagrams = [s for s in outline.sections if s.diagrams]
    if not sections_with_diagrams:
        return {"report_outline": outline}

    writer({"phase": "synthesis", "status": "running", "msg": "Generating diagrams"})

    async def generate_for_section(section: ReportSection):
        report_id = state["report_id"]
        for diagram_data in section.diagrams:
            try:
                # execute_diagram routes through the orchestrator itself for
                # the codegen step, including provider fallback.
                png_bytes, file_name = await execute_diagram(diagram_data)
                object_key = (
                    f"{report_id}/{section.order}_{_safe_object_name(file_name)}.png"
                )
                url: str | None = await upload_to_bucket(object_key, png_bytes)
                diagram_data.url = url

            except Exception:
                # A missing diagram is not fatal: the section writer is told to
                # describe the concept in prose instead.
                logger.exception(
                    f"Diagram failed for section {section.order} "
                    f"({diagram_data.diagram_type})"
                )
                diagram_data.url = None

    await asyncio.gather(*[generate_for_section(s) for s in sections_with_diagrams])
    return {"report_outline": outline}


# ─── Node: Write One Section ──────────────────────────────────────


async def write_section_node(state: SectionWriteState, writer: StreamWriter) -> dict:
    """Writes one report section. Invoked via Send."""
    section = state["section"]
    order = state["order"]

    writer(
        {
            "phase": "synthesis",
            "status": "running",
            "msg": f"Writing {order}: {section.title}",
        }
    )

    content = await get_orchestrator("write_section").run(
        write_section,
        state["goal"],
        state["outline"],
        section,
        state["claim_graph"],
        state["results"],
    )

    writer(
        {
            "phase": "synthesis",
            "status": "running",
            "msg": f"Finished {order}: {section.title}",
        }
    )

    return {"written_sections": {order: content}}


# ─── Node: Compile Report ─────────────────────────────────────────


async def compile_report_node(
    state: ResearchGraphState, writer: StreamWriter
) -> dict:
    """Assemble the written sections into the final markdown report."""
    outline = state.get("report_outline")
    written = state.get("written_sections", {})

    if outline is None:
        return {}

    sections = sorted(outline.sections, key=lambda s: s.order)
    missing = [s.order for s in sections if s.order not in written]
    if missing:
        # Downstream treats a missing section as a broken report, so fall back to
        # a placeholder rather than silently emitting a shorter document.
        logger.warning(f"Sections {missing} were never written; using placeholders")
        for order in missing:
            title = next(s.title for s in sections if s.order == order)
            written[order] = (
                f"*This section could not be generated. "
                f"(placeholder for: {title})*"
            )

    body_parts = [f"# {outline.title}", ""]
    for section in sections:
        body_parts.append(f"## {section.title}")
        body_parts.append("")
        body_parts.append(written[section.order])
        body_parts.append("")

    content = "\n".join(body_parts).strip() + "\n"
    report = Report(title=outline.title, content=content)

    writer(
        {
            "phase": "synthesis",
            "status": "finished",
            "done": True,
            "msg": "Report compiled.",
        }
    )

    return {"final_report": report}
