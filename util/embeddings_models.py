import os
import threading

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL")
DEVICE = os.getenv("DEVICE")
NORMALIZE_EMBEDDINGS = os.getenv("NORMALIZE_EMBEDDINGS")

if not MODEL or not DEVICE or not NORMALIZE_EMBEDDINGS:
    raise ValueError("请设置环境变量 MODEL, DEVICE, NORMALIZE_EMBEDDINGS")

# 先下载模型
from huggingface_hub import snapshot_download
print(f"正在下载/检查模型: {MODEL}")
snapshot_download(
    repo_id=MODEL,
    cache_dir="./models",
)

_embeddings = None
_lock = threading.Lock()
_initialized = False

def get_model_path():
    """查找本地模型路径"""
    cache_dir = "./models"
    if not os.path.exists(cache_dir):
        print(f"缓存目录不存在: {cache_dir}")
        return MODEL
    
    # MODEL 格式通常是 "org/model-name"
    model_parts = MODEL.split("/")
    if len(model_parts) != 2:
        print(f"模型名称格式不正确: {MODEL}")
        return MODEL
    
    org, model_name = model_parts
    print(f"查找模型: org={org}, model={model_name}")
    
    # HuggingFace 缓存目录格式: models--{org}--{model_name}
    expected_dir = f"models--{org}--{model_name}"
    model_cache_path = os.path.join(cache_dir, expected_dir)
    
    if os.path.exists(model_cache_path):
        print(f"找到模型缓存目录: {model_cache_path}")
        # 查找 snapshots 目录下的实际模型文件
        snapshots_dir = os.path.join(model_cache_path, "snapshots")
        if os.path.exists(snapshots_dir):
            # 获取第一个（通常也是唯一一个）快照目录
            snapshot_dirs = [d for d in os.listdir(snapshots_dir) if os.path.isdir(os.path.join(snapshots_dir, d))]
            if snapshot_dirs:
                actual_model_path = os.path.join(snapshots_dir, snapshot_dirs[0])
                print(f"找到模型快照目录: {actual_model_path}")
                return actual_model_path
    
    # 如果没找到，遍历查找
    print(f"在缓存目录中搜索模型文件...")
    for root, dirs, files in os.walk(cache_dir):
        # 检查是否包含模型配置文件
        if any(f in files for f in ["config.json", "pytorch_model.bin", "model.safetensors", "sentence_bert_config.json"]):
            print(f"找到模型文件目录: {root}")
            return root
    
    # 如果没找到，返回原始 MODEL
    print(f"未找到本地模型，使用在线模型: {MODEL}")
    return MODEL

def _init_embeddings():
    global _embeddings, _initialized
    if _initialized:
        return
        
    with _lock:
        if _initialized:
            return
            
        print(f"[Thread {threading.current_thread().ident}] 初始化嵌入模型...")
        model_path = get_model_path()
        print(f"[Thread {threading.current_thread().ident}] 模型路径: {model_path}")
        
        try:
            # 使用 SentenceTransformer 加载模型
            from sentence_transformers import SentenceTransformer
            
            # 如果本地路径存在则使用本地路径，否则使用模型名称
            if os.path.exists(model_path) and os.path.isdir(model_path):
                print(f"从本地路径加载模型: {model_path}")
                st_model = SentenceTransformer(model_path, device=DEVICE)
            else:
                print(f"从 HuggingFace 加载模型: {MODEL}")
                st_model = SentenceTransformer(MODEL, device=DEVICE)
            
            # 包装为 LangChain 兼容的格式
            _embeddings = SentenceTransformerEmbeddings(st_model, normalize_embeddings=NORMALIZE_EMBEDDINGS.lower() == 'true')
            
            # 测试模型是否正常工作
            test_result = _embeddings.embed_query("test")
            print(f"[Thread {threading.current_thread().ident}] 嵌入模型初始化成功，测试向量维度: {len(test_result)}")
            _initialized = True
        except Exception as e:
            print(f"[Thread {threading.current_thread().ident}] 嵌入模型初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise

def get_embeddings():
    global _embeddings
    if not _initialized:
        _init_embeddings()
    
    if _embeddings is None:
        raise RuntimeError("嵌入模型未正确初始化")
    
    return _embeddings


class SentenceTransformerEmbeddings:
    """兼容 LangChain 的 SentenceTransformer 包装器"""
    
    def __init__(self, model, normalize_embeddings=True):
        self.model = model
        self.normalize_embeddings = normalize_embeddings
    
    def embed_documents(self, texts):
        """嵌入文档列表"""
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def embed_query(self, text):
        """嵌入单个查询"""
        embedding = self.model.encode(
            text,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True
        )
        return embedding.tolist()
