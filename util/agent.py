import os
import logging

import requests
from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI

from tools.tool_list import tools_list
from util.DbChatMessageHistory import DbChatMessageHistory
from util.session_context import reset_current_session_id, set_current_session_id
from util.time_trial import times

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")
API_MODEL = os.getenv("API_MODEL")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", 60))
API_TEMPERATURE = float(os.getenv("API_TEMPERATURE", 0.7))
logger = logging.getLogger(__name__)
LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
OLLAMA_BASE_URL = (os.getenv("OLLAMA_BASE_URL") or "http://ollama:11434").rstrip("/")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))


def get_message_history(session_id: str) -> DbChatMessageHistory:
    return DbChatMessageHistory(session_id)


def ensure_ollama_model(model_name: str):
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/pull",
        json={"model": model_name, "stream": False},
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()


class AgentLLM:
    def __init__(self, api_key: str = None, api_url: str = None, api_model: str = None, timeout: int = None):
        timeout = timeout or API_TIMEOUT
        provider = LLM_PROVIDER

        if provider == "ollama":
            model_name = api_model or OLLAMA_CHAT_MODEL or API_MODEL
            if not model_name:
                raise ValueError("Please configure OLLAMA_CHAT_MODEL or API_MODEL when LLM_PROVIDER=ollama.")

            ensure_ollama_model(model_name)
            self.llm = ChatOpenAI(
                api_key=OLLAMA_API_KEY,
                base_url=f"{OLLAMA_BASE_URL}/v1",
                model=model_name,
                timeout=timeout,
                temperature=API_TEMPERATURE,
            )
            print(f"LLM initialized with Ollama model: {model_name}")
            return

        api_key = api_key or API_KEY
        api_url = api_url or API_URL
        api_model = api_model or API_MODEL
        timeout = timeout or API_TIMEOUT

        if not all([api_key, api_url, api_model]):
            raise ValueError("Model id, API key, and API url must be configured.")

        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=api_url,
            model=api_model,
            timeout=timeout,
            temperature=API_TEMPERATURE,
        )
        logger.info("LLM initialized.")

    @times
    def think(self, input_text: str, session_id: str):
        tool_registry = tools_list()
        history = DbChatMessageHistory(session_id=session_id)

        max_turns = 5
        max_messages = max_turns * 2
        all_history = [message for message in history.messages if message.type in {"human", "ai"}]
        history_messages = all_history[-max_messages:] if len(all_history) > max_messages else all_history

        with open("definition/IDENTITY.md", "r", encoding="utf-8") as file:
            identity_prompt = file.read()

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(identity_prompt + "\n" + tool_registry.getAvailableTools()),
                MessagesPlaceholder("chat_history"),
                HumanMessagePromptTemplate.from_template("{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )

        agent = create_openai_tools_agent(self.llm, tool_registry.getToolsList(), prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tool_registry.getToolsList(),
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            return_intermediate_steps=True,
        )

        token = set_current_session_id(session_id)
        stream = agent_executor.stream({"input": input_text, "chat_history": history_messages})

        def wrapped_stream():
            try:
                for item in stream:
                    yield item
            finally:
                reset_current_session_id(token)

        return wrapped_stream()
