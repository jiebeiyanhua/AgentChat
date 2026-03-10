import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from util.agent import AgentLLM
from util.DbChatMessageHistory import DbChatMessageHistory

app = FastAPI()
llmClient = AgentLLM()
executor = ThreadPoolExecutor()

def think_generator(input_text: str, session_id: str):
    for chunk in llmClient.think(input_text, session_id):
        yield chunk

async def generate_response(input_text: str, session_id: str):
    history = DbChatMessageHistory(session_id=session_id)
    full_response = ""
    
    try:
        print("--- 调用LLM ---")
        gen = think_generator(input_text, session_id)
        while True:
            chunk = await asyncio.get_event_loop().run_in_executor(executor, gen.__next__)
            if "output" in chunk:
                output = chunk["output"]
                print(f"AI: {output}", end="", flush=True)
                full_response += output
                yield f"data: {output}\n\n"
            elif "actions" in chunk:
                print(f"[工具调用] {chunk['actions']}")
    except StopIteration:
        history.add_message(HumanMessage(content=input_text))
        history.add_message(AIMessage(content=full_response))
    except ValueError as e:
        yield f"data: Error: {str(e)}\n\n"

@app.post("/agent-talk")
async def talk(input_text: str, session_id: str):
    return StreamingResponse(
        generate_response(input_text, session_id),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)