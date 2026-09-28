import json

from agents_service.models.decomposer_models import DiagramTypes
from agents_service.models.sub_agent_models import DiagramData

DIAGRAM_AGENT_SYSTEM_INSTRUCTIONS = """
You are a Python data visualization expert. Your only job is to write clean, self-contained
Python scripts that generate diagrams and save them as PNG files.

Rules you must always follow:
- Use matplotlib for all charts (line_chart, bar_chart).
- Use matplotlib and networkx, or matplotlib with annotated patches for block_diagram.
- For flowchart, use matplotlib with annotated patches and FancyArrowPatch — do NOT use
  graphviz or any external binary dependency.
- Never use plt.show(). Always use plt.savefig().
- The script must save to the exact filename you specify in output_filename.
- Save to the current working directory — no subdirectories, no absolute paths.
- All data must be hardcoded in the script — no file I/O, no API calls, no user input.
- Only use these libraries: matplotlib, numpy, networkx. All are pre-installed.
- The script must run to completion with no errors on the first attempt.
- Use a clean, professional visual style: readable font sizes, clear labels, a title,
  and a legend where applicable. Use tight_layout().
"""
DIAGRAM_AGENT_PROMPT = """
Generate a Python matplotlib script for the following diagram.

Diagram type: {diagram_type}
Caption: {caption}

{data_block}

Requirements:
- Save the output as a PNG file. Use a short, descriptive snake_case filename related to
  the caption (e.g. "gold_silver_prices_2019_2024.png").
- Set the figure title to: "{caption}"
- The script must be fully self-contained and runnable as-is.

Return the complete Python script in the `code` field and the exact filename in
`output_filename`.
"""


def build_data_block(diagram_data: DiagramData) -> str:
    if diagram_data.diagram_type in (DiagramTypes.LINE_CHART, DiagramTypes.BAR_CHART):
        return (
            f"Data (list of dicts — first key is X-axis, remaining keys are Y-series):\n"
            f"{json.dumps(diagram_data.tabular, indent=2)}\n\n"
            f"Plot each Y-series as a separate line/bar. "
            f"Use the key names as legend labels."
        )
    else:
        raise ValueError(
            f"diagram_type {diagram_data.diagram_type} should not use codegen"
        )
