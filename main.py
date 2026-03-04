import uuid

from langchain_core.messages import HumanMessage, AIMessage

from agent import AgentLLM
from util.DbChatMessageHistory import DbChatMessageHistory

if __name__ == "__main__":
    llmClient = AgentLLM()
    #随机session_id
    session_id = str(uuid.uuid4())
    history = DbChatMessageHistory(
        session_id=session_id,
    )
    #多轮对话
    while True:
        print("="*30)
        print("用户：")
        user_input = input()
        if user_input.lower() == "exit":
            break
        try:
            print("--- 调用LLM ---")
            full_response = ""
            for chunk in llmClient.think(user_input,session_id):
                # 如果是最终输出，则直接打印；如果是中间步骤，可忽略或选择显示
                if "output" in chunk:
                    print(f"AI: {chunk['output']}", end="", flush=True)
                    full_response += chunk["output"]
                # 如果你想查看工具调用过程，可以取消下面注释
                elif "actions" in chunk:
                    print(f"[工具调用] {chunk['actions']}")
            print()  # 最后换行

            # 保存用户消息和 AI 回复
            history.add_message(HumanMessage(content=user_input))
            history.add_message(AIMessage(content=full_response))
        except ValueError as e:
            print(e)
            break