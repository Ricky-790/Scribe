from langgraph.graph import END, StateGraph
from langgraph.types import Send

from agents_service.graph.nodes import (
    compile_report_node,
    decompose_node,
    dispatch_section_writers,
    execute_task_node,
    generate_diagrams_node,
    research_dispatcher,
    research_gather_node,
    research_supervisor_node,
    synthesize_outline_node,
    write_section_node,
)
from agents_service.graph.state import (
    ResearchGraphState,
    ResearchPhaseState,
    SectionWriteState,
)
from agents_service.models import IntentEnum

# ─── Conditional Edges ───────────────────────────────────────────


def route_after_research_dispatch(state: ResearchPhaseState):
    """
    After dispatcher, either dispatch tasks (Send) or exit subgraph.
    """
    if state.get("error"):
        return "synthesize"  # Or handle error state
    if not state["pending"]:
        return "synthesize"
    # If we got here from gather with pending tasks, dispatcher will run again
    # Actually this is handled by the loop: gather -> dispatcher
    return "dispatcher"


def route_research_subgraph_exit(state: ResearchPhaseState):
    """Routes research subgraph back to parent graph."""
    return "synthesize_outline"


# ─── Build Research Subgraph ─────────────────────────────────────


def dispatch_ready_tasks(state: ResearchPhaseState):
    plan = state["plan"]
    pending_ids = set(state["pending"])
    done_ids = set(state["task_results"].keys())
    tasks_by_id = {t.id: t for t in plan.tasks}

    ready = [
        tasks_by_id[tid]
        for tid in pending_ids
        if all(dep in done_ids for dep in tasks_by_id[tid].depends_on)
    ]

    if not ready:
        return "__end__"

    return [
        Send("execute_task_node", {"task": task, "task_results": state["task_results"]})
        for task in ready
    ]


def build_research_subgraph():
    builder = StateGraph(ResearchPhaseState)

    # 1. Supervisor initializes pending/done
    builder.add_node("supervisor", research_supervisor_node)
    builder.add_node("dispatcher", research_dispatcher)
    builder.add_node("execute_task_node", execute_task_node)
    builder.add_node("gather", research_gather_node)

    builder.set_entry_point("supervisor")
    builder.add_edge("supervisor", "dispatcher")

    # 2. Conditional edge returns Send objects for parallel dispatch
    builder.add_conditional_edges(
        "dispatcher",
        dispatch_ready_tasks,  # returns Send(...) or "__end__"
        {"__end__": END},
    )

    # 3. After parallel tasks, gather and loop
    builder.add_edge("execute_task_node", "gather")
    builder.add_edge("gather", "dispatcher")

    return builder.compile()


# ─── Build Main Graph ────────────────────────────────────────────


def build_research_graph():
    """
    Main agentic runtime graph.

    classify -> [research_topic?] -> decompose -> research_subgraph
                                          -> outline -> [parallel sections] -> compile -> END
    """
    builder = StateGraph(ResearchGraphState)

    # Add nodes
    # builder.add_node("classify", classify_node)
    builder.add_node("decompose", decompose_node)
    builder.add_node("synthesize_outline", synthesize_outline_node)
    builder.add_node("generate_diagrams", generate_diagrams_node)
    builder.add_node("write_section_node", write_section_node)
    builder.add_node("compile_report", compile_report_node)

    # Add the research subgraph as a node
    research_subgraph = build_research_subgraph()
    builder.add_node("research_subgraph", research_subgraph)

    # Entry point
    builder.set_entry_point("decompose")

    # Decompose -> research subgraph
    builder.add_edge("decompose", "research_subgraph")

    # Research subgraph -> outline
    builder.add_edge("research_subgraph", "synthesize_outline")
    builder.add_edge("synthesize_outline", "generate_diagrams")

    # Outline -> parallel section writers via Send
    builder.add_conditional_edges(
        "generate_diagrams",
        dispatch_section_writers,
        {"write_section_node": "write_section_node"},
    )

    # After all sections written -> compile
    builder.add_edge("write_section_node", "compile_report")

    # Compile -> END
    builder.add_edge("compile_report", END)

    return builder.compile()


# Singleton instance
_research_graph = None


def get_research_graph():
    global _research_graph
    if _research_graph is None:
        _research_graph = build_research_graph()
    return _research_graph
