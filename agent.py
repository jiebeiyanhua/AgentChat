import os
from functools import reduce

from dotenv import load_dotenv
from langchain_classic.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.messages import ToolMessage
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder, \
    ChatPromptTemplate
from langchain_openai import ChatOpenAI

from tools.tool_list import tools_list

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")
API_MODEL = os.getenv("API_MODEL")

class AgentLLM:
    def __init__(self,api_key:str = None,api_url:str = None,api_model:str = None,timeout:int = None):
        api_key = api_key or API_KEY
        api_url = api_url or API_URL
        api_model = api_model or API_MODEL
        timeout = timeout or int(os.getenv("API_TIMEOUT", 60))

        if not all([api_key, api_url, api_model]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")

        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=api_url,  # 注意 /v1 路径
            model=api_model,
            timeout=timeout
        )

    def think(self,input_text:str,temperature:float = 0.3):
        t_list= tools_list()

        system_message = SystemMessagePromptTemplate.from_template(
            "你是一个遵循严格角色设定的人物，代入角色身份来跟我通过手机互相聊天。" + t_list.getAvailableTools()
        )
        user_message = HumanMessagePromptTemplate.from_template("{input}")
        placeholder = MessagesPlaceholder("agent_scratchpad")

        messages = [
            system_message,
            user_message,
            placeholder
        ]

        # 3. 创建带工具调用的Agent
        prompt = ChatPromptTemplate.from_messages(messages)

        agent = create_openai_tools_agent(self.llm, t_list.getToolsList(), prompt)
        #添加温度
        agent_executor = AgentExecutor(agent=agent, tools=t_list.getToolsList(), verbose=False,temperature=temperature)

        return agent_executor.stream({"input": input_text})
