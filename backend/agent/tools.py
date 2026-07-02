"""Tool output parsing and extraction helpers for FastMCP and LangChain tools."""

import json
import re
from typing import Any
from langchain_core.messages import ToolMessage


def extract_tool_output_text(output: Any) -> str:
    """Extracts clean human-readable text from various LangChain/FastMCP tool output formats."""
    if isinstance(output, str):
        # Handle stringified Python list/dict containing 'text': '...'
        if output.startswith("[") and "'text':" in output:
            match = re.search(r"'text':\s*'(.*?)'(?:,\s*'id'|\})", output, re.DOTALL)
            if match:
                return match.group(1).replace("\\n", "\n")
        return output

    if isinstance(output, ToolMessage):
        return str(output.content)

    if isinstance(output, list):
        parts = []
        for item in output:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            elif hasattr(item, "content"):
                parts.append(str(item.content))
            elif hasattr(item, "text"):
                parts.append(str(item.text))
            else:
                parts.append(str(item))
        return "\n".join(parts) if parts else str(output)

    if isinstance(output, dict):
        if "text" in output:
            return str(output["text"])
        return json.dumps(output)

    return str(output)
