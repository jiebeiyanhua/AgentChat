import os

from dotenv import load_dotenv
from langchain_classic.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder, \
    ChatPromptTemplate
from langchain_openai import ChatOpenAI

from tools.tool_list import tools_list
from util.DbChatMessageHistory import DbChatMessageHistory
from util.time_trial import times

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")
API_MODEL = os.getenv("API_MODEL")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", 60))


def get_message_history(session_id: str) -> DbChatMessageHistory:
    return DbChatMessageHistory(session_id)

class AgentLLM:
    def __init__(self,api_key:str = None,api_url:str = None,api_model:str = None,timeout:int = None):
        api_key = api_key or API_KEY
        api_url = api_url or API_URL
        api_model = api_model or API_MODEL
        timeout = timeout or API_TIMEOUT

        if not all([api_key, api_url, api_model]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")

        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=api_url,  # 注意 /v1 路径
            model=api_model,
            timeout=timeout
        )
    @times
    def think(self,input_text:str,session_id:str):
        try:
            t_list= tools_list()

            history = DbChatMessageHistory(
                session_id=session_id,
            )

            # 在对话主循环中，获取历史消息时限制轮数
            max_turns = 5
            max_messages = max_turns * 2  # 每轮包含用户和AI两条消息
            all_history = history.messages
            if len(all_history) > max_messages:
                history_messages = all_history[-max_messages:]  # 取最后 max_messages 条
            else:
                history_messages = all_history

            with open("definition/IDENTITY.md", "r", encoding="utf-8") as f:
                identity_prompt = f.read()


            system_message = SystemMessagePromptTemplate.from_template(identity_prompt + "\n" + t_list.getAvailableTools())
            user_message = HumanMessagePromptTemplate.from_template("{input}")
            placeholder = MessagesPlaceholder("agent_scratchpad")
            chat_message = MessagesPlaceholder("chat_history")


            messages = [
                system_message,
                chat_message,
                user_message,
                placeholder
            ]

            # 3. 创建带工具调用的Agent
            prompt = ChatPromptTemplate.from_messages(messages)

            agent = create_openai_tools_agent(self.llm, t_list.getToolsList(), prompt)

            agent_executor = AgentExecutor(
                agent=agent,
                tools=t_list.getToolsList(),
                verbose=True,
                handle_parsing_errors=False,  # 处理解析错误
                max_iterations=5,  # 最大工具调用次数
                return_intermediate_steps=True  # 是否返回代理中间步骤的轨迹  除了最终的输出之外。
            )

            return agent_executor.stream({"input": input_text,"chat_history": history_messages})
        except Exception as e:
            raise e
