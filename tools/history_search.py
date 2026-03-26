from langchain_core.tools import tool

from util.DbChatMessageHistory import DbChatMessageHistory
from util.session_context import get_current_session_id


@tool
def search_early_history(query: str) -> str:
    """Search earlier history in the current session and return the most relevant excerpts."""
    session_id = get_current_session_id()
    if not session_id:
        return "No active session context is available."

    history = DbChatMessageHistory(session_id=session_id)
    messages = history.search_early_history(query=query, k=5, recent_turns_to_skip=5)
    if not messages:
        return "No relevant earlier history was found for this session."

    excerpts = []
    for index, message in enumerate(messages, start=1):
        excerpts.append(f"{index}. [{message.type}] {message.content}")
    return "\n".join(excerpts)
