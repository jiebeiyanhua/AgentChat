# PyAi

PyAi 是一个包含 FastAPI 后端、Vue 前端、PostgreSQL、Redis 和 Ollama 的智能体项目。

## 模型切换

项目现在支持两套模型接入方式，并通过环境变量切换：

- 大模型：`LLM_PROVIDER=openai` 或 `LLM_PROVIDER=ollama`
- 向量模型：`EMBEDDING_PROVIDER=huggingface` 或 `EMBEDDING_PROVIDER=ollama`

默认保持原有方式：
- 大模型继续使用 `API_KEY` / `API_URL` / `API_MODEL`
- 向量模型继续使用本地 HuggingFace / SentenceTransformer

如果切到 Ollama：
- 大模型读取 `OLLAMA_CHAT_MODEL`
- 向量模型读取 `OLLAMA_EMBED_MODEL`
- Docker 内部服务地址默认是 `http://ollama:11434`

## Docker 启动

### 1. 准备环境变量

复制 `.env.example` 为 `.env`，按你的场景填写。

### 2. 默认模式：保留原有连接

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=huggingface
API_KEY=your_api_key
API_URL=your_api_url
API_MODEL=your_api_model
MODEL=Qwen/Qwen3-Embedding-0.6B
DEVICE=cpu
NORMALIZE_EMBEDDINGS=True
```

### 3. Ollama 模式

```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_CHAT_MODEL=qwen2.5:7b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

你也可以混合使用：
- `LLM_PROVIDER=openai` + `EMBEDDING_PROVIDER=ollama`
- `LLM_PROVIDER=ollama` + `EMBEDDING_PROVIDER=huggingface`

### 4. 启动服务

```bash
docker compose up --build
```

启动完成后：
- 前端：http://localhost:5173
- 后端：http://localhost:8000
- PostgreSQL：localhost:5432
- Redis：localhost:6379
- Ollama：localhost:11434

### 5. 后台启动

```bash
docker compose up -d --build
```

### 6. 停止服务

```bash
docker compose down
```

如果要连同数据库卷和 Ollama 模型缓存一起清理：

```bash
docker compose down -v
```

## 容器说明

- `frontend`：构建 Vue 前端并通过 Nginx 提供静态页面
- `backend`：运行 FastAPI 服务
- `db`：PostgreSQL
- `redis`：缓存与会话心跳
- `ollama`：本地大模型与向量模型服务
- `ollama-init`：自动拉取 `OLLAMA_CHAT_MODEL` 和 `OLLAMA_EMBED_MODEL`

## 常用命令

查看日志：

```bash
docker compose logs -f backend
docker compose logs -f ollama
docker compose logs -f ollama-init
```

只重建后端：

```bash
docker compose up --build backend
```

只重新拉取 Ollama 模型：

```bash
docker compose up ollama-init
```

## 新增 Docker 文件

- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker-compose.yml`
- `docker/nginx.conf`
- `.dockerignore`
