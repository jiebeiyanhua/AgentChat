import os

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

MODEL = os.getenv("MODEL")
DEVICE = os.getenv("DEVICE")
NORMALIZE_EMBEDDINGS = os.getenv("NORMALIZE_EMBEDDINGS")

if not MODEL or not DEVICE or not NORMALIZE_EMBEDDINGS:
    raise ValueError("请设置环境变量 MODEL, DEVICE, NORMALIZE_EMBEDDINGS")

from huggingface_hub import snapshot_download
snapshot_download(
    repo_id=MODEL,
    cache_dir="./models",
)

def get_embeddings():
    print("初始化嵌入模型...")
    if os.path.exists("./models"):
        #获取本地模型完整地址
        path = os.listdir("./models")
        model_split = MODEL.split("/")
        model_path = MODEL
        for i in path:
            if model_split[0] in i and model_split[1] in i:
                model_path = os.path.dirname(i)
    else:
        model_path = MODEL

    embeddings = HuggingFaceEmbeddings(
        model_name=model_path,      # 中英文通用嵌入模型
        model_kwargs={'device': DEVICE},      # 如果GPU可用可改为 'cuda'
        encode_kwargs={'normalize_embeddings': NORMALIZE_EMBEDDINGS}
    )
    return embeddings