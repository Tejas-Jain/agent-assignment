from typing import Any


def openai_tools_to_gemini_declarations(tools: list[dict]) -> list[dict]:
    """Map OpenAI tool schemas to Gemini function declaration dicts."""
    declarations = []
    for tool in tools:
        fn = tool.get("function", {})
        declarations.append(
            {
                "name": fn["name"],
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return declarations
