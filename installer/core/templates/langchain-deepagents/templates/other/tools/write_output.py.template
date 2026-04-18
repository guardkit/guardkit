"""Generic JSON-line output writer tool."""

import json
import os

from langchain_core.tools import tool


@tool
def write_output(content: str, output_path: str) -> str:
    """Validates JSON content and appends it to the specified output file.

    Writes a single JSON line to the given path under the output/ directory.
    Creates parent directories if they do not exist.

    Args:
        content: A valid JSON string to write.
        output_path: Relative path under output/ (e.g., output/results.jsonl).
    """
    try:
        try:
            json.loads(content)
        except (json.JSONDecodeError, TypeError) as e:
            return f"error: content is not valid JSON — {e}"

        if not output_path.startswith("output/"):
            return "error: output_path must start with 'output/' (path traversal guard)"

        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(output_path, "a") as f:
            f.write(content + "\n")

        return f"written to {output_path}"
    except Exception as e:
        return f"error: {e}"
