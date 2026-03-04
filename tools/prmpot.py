# 2. 定义检索工具（让AI可以主动检索相关设定）
import os

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH")
DEVICE = os.getenv("DEVICE")
NORMALIZE_EMBEDDINGS = os.getenv("NORMALIZE_EMBEDDINGS")

embeddings = HuggingFaceEmbeddings(
    model_name=MODEL_PATH,      # 中英文通用嵌入模型
    model_kwargs={'device': DEVICE},      # 如果GPU可用可改为 'cuda'
    encode_kwargs={'normalize_embeddings': NORMALIZE_EMBEDDINGS}
)

@tool
def retrieve_profile(query: str) -> str:
    """根据用户输入检索最相关的个人设定、AI身份或价值观片段。"""
    # 1. 加载所有设定文件并构建向量库
    full_text = ""
    for file in ["definition/USER.md", "definition/IDENTITY.md", "definition/SOUL.md"]:
        try:
            with open(file, "r", encoding='utf-8', errors='ignore') as f:
                full_text += f"\n\n--- {file} ---\n" + f.read()
                f.close()
        except FileNotFoundError:
            continue
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=50,
        separators=["#"],
        length_function=len)
    chunks = splitter.split_text(full_text)
    # 使用自定义 embeddings 创建 Chroma 向量库，并返回检索器
    vectorstore = Chroma.from_texts(chunks, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})  # 返回检索器
    docs = retriever.invoke(query)
    return "\n\n".join([doc.page_content for doc in docs])
