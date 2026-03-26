from contextvars import ContextVar, Token

current_session_id: ContextVar[str | None] = ContextVar("current_session_id", default=None)


def set_current_session_id(session_id: str) -> Token:
    return current_session_id.set(session_id)


def reset_current_session_id(token: Token) -> None:
    current_session_id.reset(token)


def get_current_session_id() -> str | None:
    return current_session_id.get()
