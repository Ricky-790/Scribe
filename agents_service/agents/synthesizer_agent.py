import os

from pydantic_ai import Agent

from agents_service.models import (
    Claim,
    ClaimGraph,
    ClaimStatus,
    Report,
    ReportOutline,
    ReportSection,
    TaskResult,
)
from agents_service.models.synthesizer_models import GeneratedDiagram
from agents_service.pipeline.orchestrator import build_model
from agents_service.pipeline.rate_limiting import Provider
from agents_service.prompts import (
    OUTLINE_AGENT_INSTRUCTIONS,
    OUTLINE_PROMPT_TEMPLATE,
    SECTION_WRITER_INSTRUCTIONS,
    SECTION_WRITER_PROMPT_TEMPLATE,
)
from custom_logger import get_logger

outline_model_name = os.getenv("OUTLINE_MODEL", "gemini-3.1-flash-lite")
section_model_name = os.getenv("SECTION_WRITER_MODEL", "gemini-3.1-flash-lite")

logger = get_logger()


def get_outline_agent(
    model_name: str | None = None, provider: Provider | None = None
):
    """Build the agent. Overrides let the orchestrator supply a fallback model."""
    model = build_model(
        model_name or outline_model_name, provider or Provider.GOOGLE
    )
    outline_agent = Agent(
        model,
        output_type=ReportOutline,
        instructions=OUTLINE_AGENT_INSTRUCTIONS,
    )
    return outline_agent


def get_section_writer_agent(
    model_name: str | None = None, provider: Provider | None = None
):
    """Build the agent. Overrides let the orchestrator supply a fallback model."""
    model = build_model(
        model_name or section_model_name, provider or Provider.GOOGLE
    )
    section_writer_agent = Agent(
        model,
        output_type=str,
        instructions=SECTION_WRITER_INSTRUCTIONS,
    )
    return section_writer_agent


def _format_claim(claim: Claim, results: dict[str, TaskResult]) -> str:
    """Render one claim with its evidence and any supporting task detail."""
    lines = [f"[{claim.claim_id}] {claim.statement}"]

    if claim.status == ClaimStatus.CONFLICTING:
        lines.append("  STATUS: CONFLICTING — sources disagree on this point.")
    elif claim.status == ClaimStatus.UNSUPPORTED:
        lines.append("  STATUS: UNSUPPORTED — treat with caution and hedge.")

    if claim.evidence:
        for evidence in claim.evidence:
            title = evidence.source.title or evidence.source.url
            lines.append(f"  - {title} <{evidence.source.url}>")
            if evidence.quote:
                lines.append(f'      "{evidence.quote}"')
            else:
                lines.append("      (no direct quotation was captured)")

    return "\n".join(lines)


def _build_claims_block(
    claim_ids: list[str],
    claim_graph: ClaimGraph,
    results: dict[str, TaskResult],
) -> str:
    if not claim_ids:
        return "(no specific claims — synthesize from the goal and outline instead)"

    by_id = {c.claim_id: c for c in claim_graph.claims}
    blocks = [
        _format_claim(by_id[claim_id], results)
        for claim_id in claim_ids
        if claim_id in by_id
    ]
    return "\n\n".join(blocks) if blocks else "(no claims available for this section)"


def _build_all_claims_block(
    claim_graph: ClaimGraph, results: dict[str, TaskResult]
) -> str:
    if not claim_graph.claims:
        return "(no claims were established)"
    return "\n\n".join(
        _format_claim(claim, results) for claim in claim_graph.claims
    )


def _build_conflicts_block(claim_graph: ClaimGraph) -> str:
    conflicts = [c for c in claim_graph.claims if c.status == ClaimStatus.CONFLICTING]
    if not conflicts:
        return ""

    lines = []
    for claim in conflicts:
        others = ", ".join(claim.conflicts) or "unlinked"
        lines.append(f"- {claim.claim_id}: {claim.statement} (conflicts with {others})")
    return (
        "The research produced conflicting findings on the following points. Do not "
        "silently pick a side. Present the disagreement and say what is driving it.\n"
        + "\n".join(lines)
    )


def _build_outline_summary(outline: ReportOutline) -> str:
    lines = [
        f"{s.order}. {s.title} — {s.description}"
        for s in sorted(outline.sections, key=lambda s: s.order)
    ]
    return "\n".join(lines)


def _build_diagram_instruction(section: ReportSection) -> str:
    if not section.diagrams:
        return ""

    successful = [d for d in section.diagrams if d.url is not None]
    failed = [d for d in section.diagrams if d.url is None]

    parts = []

    if successful:
        embeds = "\n".join(f"![{d.caption}]({d.url})" for d in successful)
        parts.append(
            f"The following diagram(s) have been generated for this section. "
            f"Embed each one naturally after the paragraph that introduces what it visualizes:\n"
            f"{embeds}"
        )

    if failed:
        failed_captions = "\n".join(f"- {d.caption}" for d in failed)
        parts.append(
            f"The following diagram(s) could not be generated due to a technical error. "
            f"For each one, write a descriptive paragraph in its place that conveys the "
            f"same information the diagram would have shown:\n"
            f"{failed_captions}"
        )

    return "\n\n" + "\n\n".join(parts) + "\n"


def enrich_outline_with_diagrams(
    outline: ReportOutline,
    results: dict[str, TaskResult],
    claim_graph: ClaimGraph,
) -> ReportOutline:
    """
    Attach diagram data to each section.

    Sections reference claims, and diagram data lives on the task result, so this
    resolves claim → supporting_tasks → diagram_data. A diagram used by several
    sections of the same report is rendered once per section that asks for it.
    """
    task_ids_by_claim = {
        claim.claim_id: claim.supporting_tasks for claim in claim_graph.claims
    }
    seen_keys: set[tuple] = set()

    for section in outline.sections:
        diagrams: list[GeneratedDiagram] = []
        for claim_id in section.relevant_claim_ids:
            for task_id in task_ids_by_claim.get(claim_id, []):
                result = results.get(task_id)
                if result is None or not result.diagram_data:
                    continue
                key = (task_id, section.order)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                diagrams.append(
                    GeneratedDiagram(**result.diagram_data.model_dump(), url=None)
                )
        section.diagrams = diagrams
        logger.info(
            f"Section '{section.title}' (claims={section.relevant_claim_ids}) "
            f"-> {len(diagrams)} diagram(s)"
        )
    return outline


async def generate_outline(
    outline_agent: Agent,
    goal: str,
    claim_graph: ClaimGraph,
    results: dict[str, TaskResult],
) -> ReportOutline:
    prompt = OUTLINE_PROMPT_TEMPLATE.format(
        goal=goal,
        claims_block=_build_all_claims_block(claim_graph, results),
        conflicts_block=_build_conflicts_block(claim_graph),
    )
    result = await outline_agent.run(prompt)
    outline = result.output
    return enrich_outline_with_diagrams(
        outline=outline, results=results, claim_graph=claim_graph
    )


async def write_section(
    section_writer_agent: Agent,
    goal: str,
    outline: ReportOutline,
    section: ReportSection,
    claim_graph: ClaimGraph,
    results: dict[str, TaskResult],
) -> str:
    claims_block = _build_claims_block(
        section.relevant_claim_ids, claim_graph, results
    )
    conflicts_block = _build_conflicts_block(claim_graph)
    outline_summary = _build_outline_summary(outline)
    diagram_instruction = _build_diagram_instruction(section)

    prompt = SECTION_WRITER_PROMPT_TEMPLATE.format(
        goal=goal,
        outline_summary=outline_summary,
        section_title=section.title,
        section_description=section.description,
        findings_block=claims_block,
        conflicts_block=conflicts_block,
        diagram_instruction=diagram_instruction,
    )
    result = await section_writer_agent.run(prompt)
    return result.output
