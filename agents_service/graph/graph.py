from langgraph.graph import END, StateGraph
from langgraph.types import Send

from agents_service.graph.nodes import (
    build_claims_node,
    challenge_node,
    compile_report_node,
    decompose_node,
    execute_task_node,
    generate_diagrams_node,
    plan_research_node,
    replan_node,
    synthesize_outline_node,
    write_section_node,
)
from agents_service.graph.state import (
    ResearchGraphState,
    SectionWriteState,
    TaskExecutionState,
)
from custom_logger import get_logger

# Ceiling on correction rounds. Each one costs a full parallel research pass
# plus two consolidation agents, so this bounds the worst case rather than
# trusting the challenge stage to terminate on its own.
MAX_REPLAN_ROUNDS = 2

logger = get_logger()


# ─── Conditional Edges ───────────────────────────────────────────


def dispatch_research_tasks(state: ResearchGraphState) -> list[Send]:
    """
    Fan every outstanding task out to a research agent in parallel.

    Tasks already present in `task_results` are skipped, so a replan round runs
    only the newly added tasks while round 1's results are carried forward.
    """
    tasks = [t for t in (state.get("plan").tasks if state.get("plan") else [])]
    tasks += state.get("replan_tasks", [])

    completed = set(state.get("task_results", {}))
    outstanding = [t for t in tasks if t.id not in completed]

    prior_claims, known_problems = _prior_round_context(state)

    return [
        Send(
            "execute_task_node",
            TaskExecutionState(
                task=task,
                results_so_far=state.get("task_results", {}),
                prior_claims=prior_claims,
                known_problems=known_problems,
            ),
        )
        for task in outstanding
    ]


def _prior_round_context(state: ResearchGraphState) -> tuple[list[str], list[str]]:
    """
    What a replan-round researcher should know before starting.

    On the first round this is empty and the agent is unaware of any prior
    attempt. On a correction round it gets the claims already built and the
    problems the challenge stage raised, so it does not repeat the work that
    was rejected.
    """
    if not state.get("claim_graph"):
        return [], []

    prior_claims = [claim.statement for claim in state["claim_graph"].claims]

    challenge = state.get("challenge_result")
    known_problems = (
        [
            f"{issue.claim_id}: {issue.problem} (missing: {issue.missing_evidence})"
            for issue in challenge.issues
        ]
        if challenge
        else []
    )
    return prior_claims, known_problems


def route_after_challenge(state: ResearchGraphState) -> str:
    """
    Decide whether to attempt a correction round, or move to synthesis.

    This only decides whether to *try* a replan. Whether one actually happens
    depends on the replan stage producing usable tasks, which is only known after
    this decision — so `route_after_replan` makes the second call. Deciding both
    here would always see an empty plan and never loop.
    """
    challenge = state.get("challenge_result")
    if challenge is None or challenge.status != "needs_research":
        return "synthesize_outline"

    if state.get("replan_count", 0) >= MAX_REPLAN_ROUNDS:
        logger.info(
            f"Challenge requested more research but the {MAX_REPLAN_ROUNDS}-round "
            f"cap is reached; writing up what we have."
        )
        return "synthesize_outline"

    return "replan"


def route_after_replan(state: ResearchGraphState) -> str:
    """
    Continue into the next research round, or give up and write up.

    The round cap is enforced in `route_after_challenge`, before any research is
    planned. Re-checking it here would discard tasks this node just produced —
    so the cap would silently mean "attempts" rather than "research rounds".
    """
    replan = state.get("replan_plan")
    if replan is None or not replan.tasks:
        logger.info("Replan produced no tasks; proceeding to synthesis")
        return "synthesize_outline"

    return "plan_research"


def dispatch_section_writers(state: ResearchGraphState) -> list[Send]:
    """Fan out one writer per report section."""
    outline = state["report_outline"]
    return [
        Send(
            "write_section_node",
            SectionWriteState(
                goal=state["query"],
                outline=outline,
                section=section,
                claim_graph=state["claim_graph"],
                results=state["task_results"],
                order=section.order,
            ),
        )
        for section in sorted(outline.sections, key=lambda s: s.order)
    ]


# ─── Build Main Graph ────────────────────────────────────────────


def build_research_graph():
    """
    Research runtime.

    plan -> [parallel research] -> build_claims -> challenge
                                                 ├─ sufficient ──→ outline
                                                 └─ needs_research → replan ─┐
                                                                          │
                              ┌───────────────────────────────────────────┘
                              ▼ (bounded by MAX_REPLAN_ROUNDS)
                    plan_research -> [parallel research] -> build_claims -> challenge

    outline -> [diagrams] -> [parallel sections] -> compile -> END
    """
    builder = StateGraph(ResearchGraphState)

    builder.add_node("decompose", decompose_node)
    builder.add_node("plan_research", plan_research_node)
    builder.add_node("execute_task_node", execute_task_node)
    builder.add_node("build_claims", build_claims_node)
    builder.add_node("challenge", challenge_node)
    builder.add_node("replan", replan_node)
    builder.add_node("synthesize_outline", synthesize_outline_node)
    builder.add_node("generate_diagrams", generate_diagrams_node)
    builder.add_node("write_section_node", write_section_node)
    builder.add_node("compile_report", compile_report_node)

    builder.set_entry_point("decompose")

    # Planning is shared by every round: the first pass generates a plan, a
    # replan round just re-enters the same fan-out with the tasks it added.
    builder.add_conditional_edges(
        "decompose", dispatch_research_tasks, ["execute_task_node"]
    )
    builder.add_conditional_edges(
        "plan_research", dispatch_research_tasks, ["execute_task_node"]
    )
    builder.add_edge("execute_task_node", "build_claims")

    # Consolidation and review.
    builder.add_edge("build_claims", "challenge")
    builder.add_conditional_edges(
        "challenge",
        route_after_challenge,
        {"replan": "replan", "synthesize_outline": "synthesize_outline"},
    )
    builder.add_conditional_edges(
        "replan",
        route_after_replan,
        {"plan_research": "plan_research", "synthesize_outline": "synthesize_outline"},
    )

    # Synthesis.
    builder.add_edge("synthesize_outline", "generate_diagrams")
    builder.add_conditional_edges(
        "generate_diagrams", dispatch_section_writers, ["write_section_node"]
    )
    builder.add_edge("write_section_node", "compile_report")
    builder.add_edge("compile_report", END)

    return builder.compile()


# Singleton instance
_research_graph = None


def get_research_graph():
    global _research_graph
    if _research_graph is None:
        _research_graph = build_research_graph()
    return _research_graph
