from langchain_core.tools import tool

from util.knowledge_base import search_knowledge_base


@tool
def retrieve_profile(query: str) -> str:
    """Search the database knowledge base and return the most relevant snippets."""
    results = search_knowledge_base(query, k=5)
    if not results:
        return "知识库中没有检索到相关内容。"

    return "\n\n".join(
        f"[{item['source_name']} | {item['source_type']}]\n{item['content']}"
        for item in results
    )
