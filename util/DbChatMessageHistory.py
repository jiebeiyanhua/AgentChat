import os
import uuid
from datetime import datetime, timezone
from typing import List

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, message_to_dict
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH")
DEVICE = os.getenv("DEVICE")
NORMALIZE_EMBEDDINGS = os.getenv("NORMALIZE_EMBEDDINGS")

embeddings = HuggingFaceEmbeddings(
    model_name=MODEL_PATH,      # 中英文通用嵌入模型
    model_kwargs={'device': DEVICE},      # 如果GPU可用可改为 'cuda'
    encode_kwargs={'normalize_embeddings': NORMALIZE_EMBEDDINGS}
)

class DbChatMessageHistory(BaseChatMessageHistory):
    def __init__(
            self,
            session_id: str,
            collection_name: str = "history",
            persist_directory: str = "./chroma_db",
    ):
        self.session_id = session_id
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        # 初始化 Chroma 集合
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,  # 即使为 None，Chroma 也可以存储纯文本（只是无法向量检索）
            persist_directory=persist_directory,
        )

    @property
    def messages(self) -> List[BaseMessage]:
        """获取当前会话的所有消息，按时间升序排列"""
        # 从 Chroma 中查询所有 session_id 匹配的消息
        results = self.vectorstore.get(
            where={"session_id": self.session_id},
            include=["metadatas", "documents"],
        )
        if not results["ids"]:
            return []

        # 将文档和元数据组合，按时间戳排序
        metadatas = results["metadatas"]
        documents = results["documents"]
        # 每条消息的文档内容是序列化的消息字典
        message_dicts = []
        for meta, doc in zip(metadatas, documents):
            # 文档内容存储为 JSON 字符串，需反序列化
            import json
            msg_dict = json.loads(doc)
            msg_dict["metadata"] = meta  # 可选的额外元数据
            message_dicts.append((meta["timestamp"], msg_dict))

        # 按时间戳升序排序
        message_dicts.sort(key=lambda x: x[0])
        # 恢复为 BaseMessage 对象
        messages = messages_from_dict([msg for _, msg in message_dicts])
        return messages

    def add_message(self, message: BaseMessage) -> None:
        """添加一条消息到历史记录"""
        # 将消息转换为字典并序列化为 JSON 字符串
        msg_dict = message_to_dict(message)
        # 添加额外元数据：session_id, timestamp, 消息类型等
        metadata = {
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": msg_dict["type"],
        }
        # 文档内容：存储整个消息字典的 JSON 字符串
        import json
        doc_content = json.dumps(msg_dict, ensure_ascii=False)

        # 生成唯一 ID
        doc_id = str(uuid.uuid4())

        # 添加到 Chroma
        self.vectorstore.add_texts(
            texts=[doc_content],
            metadatas=[metadata],
            ids=[doc_id],
        )

    def clear(self) -> None:
        """清空当前会话的所有历史消息"""
        # 获取所有匹配 session_id 的文档 ID
        results = self.vectorstore.get(where={"session_id": self.session_id})
        ids = results["ids"]
        if ids:
            self.vectorstore.delete(ids)

    def search_similar(self, query: str, k: int = 5) -> List[BaseMessage]:
        """
        根据语义相似性检索历史消息（需要 embedding_function）
        返回按相似度排序的消息列表
        """
        if not self.vectorstore._embedding_function:
            raise ValueError("未设置 embedding_function，无法进行语义检索")

        docs = self.vectorstore.similarity_search(
            query,
            k=k,
            filter={"session_id": self.session_id},
        )
        # 从文档内容反序列化为消息对象
        import json
        messages = []
        for doc in docs:
            msg_dict = json.loads(doc.page_content)
            # 恢复消息对象
            messages.append(messages_from_dict([msg_dict])[0])
        return messages
