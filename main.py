import os
import asyncio

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from util.agent import AgentLLM
from util.DbChatMessageHistory import DbChatMessageHistory

app = FastAPI()
llmClient = AgentLLM()

async def generate_response(input_text: str, session_id: str):
    history = DbChatMessageHistory(session_id=session_id)
    full_response = ""
    
    try:
        print("--- 调用LLM ---")
        
        # 使用 asyncio.to_thread 将同步生成器转换为异步
        loop = asyncio.get_event_loop()
        
        def run_think():
            return list(llmClient.think(input_text, session_id))
        
        chunks = await loop.run_in_executor(None, run_think)
        
        for chunk in chunks:
            if "output" in chunk:
                output = chunk["output"]
                print(f"AI: {output}", end="", flush=True)
                full_response += output
                yield f"data: {output}\n\n"
            elif "actions" in chunk:
                print(f"[工具调用] {chunk['actions']}")
        
        history.add_message(HumanMessage(content=input_text))
        history.add_message(AIMessage(content=full_response))
    except Exception as e:
        print(f"Error: {e}")
        yield f"data: Error: {str(e)}\n\n"

@app.post("/agent-talk")
async def talk(input_text: str, session_id: str):
    return StreamingResponse(
        generate_response(input_text, session_id),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
