
from agent import AgentLLM
if __name__ == "__main__":
    #多轮对话
    while True:
        print("="*30)
        print("用户：")
        text = input()
        if text == "exit":
            break
        try:
            llmClient = AgentLLM()
            print("--- 调用LLM ---")
            for chunk in llmClient.think(text):
                # 如果是最终输出，则直接打印；如果是中间步骤，可忽略或选择显示
                if "output" in chunk:
                    print(f"AI: {chunk["output"]}", end="", flush=True)
                # 如果你想查看工具调用过程，可以取消下面注释
                elif "actions" in chunk:
                    print(f"[工具调用] {chunk['actions']}")
            print()  # 最后换行
        except ValueError as e:
            print(e)
            break