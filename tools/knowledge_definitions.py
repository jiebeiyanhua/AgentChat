from langchain_core.tools import tool

from util.knowledge_base import list_knowledge_definitions


@tool
def get_knowledge_definitions() -> str:
    """List all available knowledge base definitions before selecting a source to retrieve."""
    definitions = list_knowledge_definitions()
    if not definitions:
        return "当前没有可用的知识库定义。"

    return "\n\n".join(
        (
            f"source_key: {item.source_key}\n"
            f"source_name: {item.source_name}\n"
            f"source_type: {item.source_type}\n"
            f"description: {item.description}\n"
            f"chunk_count: {item.chunk_count}\n"
            f"file_path: {item.file_path or '-'}"
        )
        for item in definitions
    )

