import asyncio

from e2b_code_interpreter import Sandbox
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, UserPromptPart

from agents_service.agents.diagram_agent import generate_diagram_code
from agents_service.models import DiagramAgentOutput, DiagramData, DiagramTypes
from agents_service.pipeline.rate_limiting import run_with_retry
from agents_service.prompts import DIAGRAM_AGENT_PROMPT
from custom_logger import get_logger

logger = get_logger()

DIAGRAM_DEPS = ["matplotlib", "numpy", "networkx"]
MAX_CORRECTION_ATTEMPTS = 3


class DiagramGenerationError(Exception):
    """Raised when Diagram generation fails. Catch this error, let section writer know that diagram failed, make amends needed"""

    pass


def _build_data_block(diagram_data: DiagramData) -> str:
    import json

    if diagram_data.diagram_type in (DiagramTypes.LINE_CHART, DiagramTypes.BAR_CHART):
        return (
            f"Data (list of dicts — first key is X-axis, remaining keys are Y-series):\n"
            f"{json.dumps(diagram_data.tabular, indent=2)}\n\n"
            f"Plot each Y-series as a separate line/bar. Use key names as legend labels."
        )
    raise ValueError(f"{diagram_data.diagram_type} should not use codegen")


async def _render_mermaid(mermaid_str: str) -> bytes:
    import base64

    import httpx

    encoded = base64.urlsafe_b64encode(mermaid_str.encode()).decode()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"https://mermaid.ink/img/{encoded}")
        response.raise_for_status()
        return response.content


async def _run_codegen_sandbox(diagram_data: DiagramData) -> tuple[bytearray, str]:
    last_error: str | None = None
    last_code: str | None = None

    with Sandbox.create() as sandbox:
        install = sandbox.commands.run(f"pip install {' '.join(DIAGRAM_DEPS)} -q")
        if install.exit_code != 0:
            raise DiagramGenerationError(
                f"Dependency installation failed:\n{install.stderr}"
            )

        for attempt in range(MAX_CORRECTION_ATTEMPTS):
            if attempt == 0:
                prompt = DIAGRAM_AGENT_PROMPT.format(
                    diagram_type=diagram_data.diagram_type,
                    caption=diagram_data.caption,
                    data_block=_build_data_block(diagram_data),
                )
            else:
                prompt = f"""You were asked to generate a {diagram_data.diagram_type} diagram.
                    Caption: {diagram_data.caption}
                    Data:{_build_data_block(diagram_data)}
                    Your previous output was:
                    ```python{last_code}```
                    It failed with this error:
                    ```{last_error}```
                    Fix the code and output the correct output."""

            result = await run_with_retry(
                generate_diagram_code,
                prompt,
                provider="nvidia",
            )
            output: DiagramAgentOutput = result.output

            sandbox.files.write("/tmp/diagram.py", output.code)
            exec_result = sandbox.commands.run("python /tmp/diagram.py", cwd="/tmp")

            if exec_result.exit_code == 0:
                png_bytes = sandbox.files.read(
                    f"/tmp/{output.output_filename}.png", format="bytes"
                )
                return png_bytes, output.output_filename

            last_error = exec_result.stderr
            last_code = output.code
            logger.warning(f"Diagram attempt {attempt + 1} failed:\n{last_error}")

        raise DiagramGenerationError(
            f"Diagram codegen failed after {MAX_CORRECTION_ATTEMPTS} attempts"
        )


async def execute_diagram(diagram_data: DiagramData) -> tuple[bytearray, str]:
    """
    Entry point. Routes to mermaid.ink or codegen sandbox based on diagram_type.
    """
    if diagram_data.diagram_type in (
        DiagramTypes.FLOW_CHART,
        DiagramTypes.BLOCK_DIAGRAM,
    ):
        png_bytes = await _render_mermaid(diagram_data.mermaid)
        return bytearray(png_bytes), diagram_data.caption
    else:
        try:
            png_bytes, file_name = await _run_codegen_sandbox(diagram_data)
            return png_bytes, file_name
        except DiagramGenerationError:
            return None
