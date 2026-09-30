"""Pipeline helpers.

Deliberately does not re-export the legacy ``Pipeline`` class from
``pipeline.pipeline``. That module predates the LangGraph rewrite, nothing
imports it, and eagerly importing it here created a circular dependency: agent
modules import ``pipeline.orchestrator``, which runs this package's
``__init__``, which pulled in the legacy orchestrator and back into the agents.

Import the submodules directly instead:

    from agents_service.pipeline.orchestrator import get_orchestrator
"""
