from langchain_core.tools import tool

from util.knowledge_base import search_knowledge_base


@tool
def retrieve_profile(query: str, source_key: str) -> str:
    """Retrieve relevant snippets from a selected knowledge base source. Call get_knowledge_definitions first and pass the chosen source_key."""
    results = search_knowledge_base(query=query, source_key=source_key, k=5)
    if not results:
        return f"知识库 {source_key} 中没有检索到相关内容。"

    return "\n\n".join(
        f"[{item['source_name']} | {item['source_type']} | similarity={item['similarity']:.4f}]\n{item['content']}"
        for item in results
    )

