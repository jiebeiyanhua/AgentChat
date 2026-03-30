# PyAi - 智能AI代理系统

PyAi 是一个包含 FastAPI 后端、Vue 前端、PostgreSQL、Redis 和 Ollama 的智能体项目，能够通过工具调用增强大语言模型的能力，支持多种实用功能，并使用向量数据库存储对话历史。

## 项目功能

- 🤖 **智能对话**：基于大语言模型的多轮对话能力，支持 OpenAI 和 Ollama 模型
- 📅 **时间查询**：获取当前时间信息
- 🔍 **网络搜索**：进行网页搜索和获取热搜数据
- ☁️ **天气查询**：获取指定城市的天气情况
- 👤 **用户信息**：检索用户资料和身份信息
- 📚 **对话历史管理**：使用向量数据库存储和管理对话历史
- 🔎 **语义相似性检索**：基于语义相似性检索历史消息
- 🚀 **API接口**：提供FastAPI接口，支持WebSocket实时通信
- 💻 **前端界面**：基于Vue 3的现代化前端界面
- 🔧 **安全 shell**：执行安全的shell命令
- 🔍 **历史搜索**：搜索历史对话内容
- 📖 **知识库管理**：管理和检索知识库内容

## 模型切换

项目支持两套模型接入方式，并通过 `config/app_config.json` 切换：

- 大模型：`llm.provider = openai` 或 `llm.provider = ollama`
- 向量模型：`embedding.provider = huggingface` 或 `embedding.provider = ollama`

默认保持原有方式：
- 大模型继续使用 `llm.api_key` / `llm.api_url` / `llm.api_model`
- 向量模型继续使用本地 HuggingFace / SentenceTransformer

如果切到 Ollama：
- 大模型读取 `ollama.chat_model`
- 向量模型读取 `ollama.embed_model`
- Docker 内部服务地址默认是 `http://ollama:11434`

## 项目结构

```
PyAi/
├── controller/        # 控制器
│   ├── chat_controller.py    # 聊天相关接口
│   └── config_controller.py  # 配置相关接口
├── definition/        # 定义文件（身份、记忆等）
│   ├── IDENTITY.md
│   ├── SOUL-example.md
│   └── USER-example.md
├── docker/            # Docker 相关配置
│   └── nginx.conf     # Nginx 配置
├── tools/             # 工具实现
│   ├── current_time.py    # 获取当前时间
│   ├── history_search.py  # 搜索历史对话
│   ├── knowledge_definitions.py # 知识库定义
│   ├── prmpot.py          # 检索用户资料
│   ├── safe_shell.py      # 安全shell命令执行
│   ├── search.py          # 网页搜索和热搜
│   ├── tool_executor.py   # 工具执行器
│   ├── tool_list.py       # 工具列表管理
│   └── weather.py         # 获取天气信息
├── util/              # 工具类
│   ├── DbChatMessageHistory.py # 对话历史管理
│   ├── agent.py           # 核心Agent实现
│   ├── db_models.py       # 数据库模型
│   ├── embeddings_models.py # 嵌入模型
│   ├── knowledge_base.py  # 知识库管理
│   ├── redis_client.py    # Redis客户端
│   ├── session_context.py # 会话上下文管理
│   ├── time_trial.py      # 时间测试工具
│   └── time_utils.py      # 时间工具函数
├── web/               # 前端界面
│   ├── public/        # 静态资源
│   ├── src/           # 源代码
│   │   ├── utils/     # 工具函数
│   │   ├── views/     # 页面组件
│   │   ├── App.vue    # 应用入口
│   │   └── main.ts    # 主文件
│   ├── package.json   # 前端依赖
│   └── vite.config.ts # Vite配置
├── .dockerignore      # Docker忽略文件
├── config/
│   └── app_config.example.json  # JSON 配置示例
├── .gitignore         # Git忽略文件
├── Dockerfile.backend # 后端Dockerfile
├── Dockerfile.frontend # 前端Dockerfile
├── README.md          # 项目说明
├── docker-compose.yml # Docker Compose配置
├── init_db.sql        # 数据库初始化脚本
├── main.py            # 主入口文件（FastAPI应用）
└── requirements.txt   # 项目依赖
```

## Docker 启动

### 1. 准备 JSON 配置

复制 `config/app_config.example.json` 为 `config/app_config.json`，按你的场景填写。

### 2. 默认模式：保留原有连接

```json
{
  "llm": {
    "provider": "openai",
    "api_key": "your_api_key",
    "api_url": "your_api_url",
    "api_model": "your_api_model"
  },
  "embedding": {
    "provider": "huggingface",
    "model": "Qwen/Qwen3-Embedding-0.6B",
    "device": "cpu",
    "normalize_embeddings": true
  }
}
```

### 3. Ollama 模式

```json
{
  "llm": {
    "provider": "ollama"
  },
  "embedding": {
    "provider": "ollama"
  },
  "ollama": {
    "chat_model": "qwen2.5:7b",
    "embed_model": "nomic-embed-text"
  }
}
```

你也可以混合使用：
- `llm.provider=openai` + `embedding.provider=ollama`
- `llm.provider=ollama` + `embedding.provider=huggingface`

## MCP 扩展接入

项目现在支持在启动阶段自动初始化多个 MCP Server，并将其工具自动注册给 Agent。

可用配置方式：

- 默认使用 `config/app_config.json`
- 也可以通过 `APP_CONFIG_FILE` 指向其他 JSON 文件

支持的 transport：

- `stdio`
- `sse`
- `streamable_http`

示例：

```json
{
  "mcp": {
    "fail_fast": false,
    "servers": [
      {
        "name": "dingtalk",
        "transport": "streamable_http",
        "url": "https://your-dingtalk-mcp.example.com/mcp",
        "headers": {
          "Authorization": "Bearer your-token"
        }
      },
      {
        "name": "feishu",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "your-feishu-mcp-server"]
      }
    ]
  }
}
```

启动后可通过接口查看连接状态：

```bash
GET /mcp/servers
```

使用说明：

- `mcp.fail_fast` 为 `true` 时，只要有一个 MCP 初始化失败，应用启动就会报错。
- `servers` 中每个扩展都需要唯一的 `name` 和合法的 `transport`。
- `stdio` 模式需要配置 `command`，通常还会配合 `args` 与 `env`。
- `sse` / `streamable_http` 模式需要配置 `url`，如有鉴权可补充 `headers`。
- 可通过 `enabled: false` 临时禁用某个扩展而不删除配置。
- 配置生效后，可在前端 MCP 页面或 `GET /mcp/servers` 中查看连接状态和工具列表。

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

## 非 Docker 启动

### 1. 环境配置

1. 克隆项目到本地

2. 安装后端依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 安装前端依赖：
   ```bash
   cd web
   npm install
   ```

4. 配置 JSON 文件：
   - 复制 `config/app_config.example.json` 为 `config/app_config.json`
   - 编辑 `config/app_config.json`，填写相关信息

5. 启动 PostgreSQL 和 Redis 服务

### 2. 运行项目

#### 后端服务

```bash
python main.py
```

服务将在 `http://0.0.0.0:8000` 上运行。

#### 前端开发服务

```bash
cd web
npm run dev
```

前端服务将在 `http://localhost:5173` 上运行。

#### 前端构建

```bash
cd web
npm run build
```

构建后的静态文件将位于 `web/dist` 目录。

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

## API接口

### `GET /agent-history`

**参数**：
- `session_id`：会话ID，用于区分不同的对话会话

**返回**：
- 对话历史列表，包含用户和AI的消息

**示例请求**：
```bash
curl "http://localhost:8000/agent-history?session_id=user123"
```

### `WebSocket /ws/agent-talk`

**用途**：实时对话接口，支持流式响应

**消息类型**：
- 客户端发送：
  - 聊天消息：`{"input_text": "问题内容", "session_id": "会话ID"}`
  - 心跳消息：`{"type": "heartbeat", "session_id": "会话ID"}`

- 服务器响应：
  - 文本片段：`{"type": "chunk", "content": "文本内容"}`
  - 工具调用：`{"type": "action", "content": "工具调用信息"}`
  - 错误信息：`{"type": "error", "message": "错误信息"}`
  - 完成信息：`{"type": "done", "message": "[DONE]"}`
  - 心跳响应：`{"type": "heartbeat_ack", "session_id": "会话ID"}`

**示例连接**：
```javascript
const socket = new WebSocket('ws://localhost:8000/ws/agent-talk');

// 发送消息
socket.send(JSON.stringify({
  input_text: '今天天气怎么样？',
  session_id: 'user123'
}));

// 接收消息
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'chunk':
      console.log('AI:', data.content);
      break;
    case 'action':
      console.log('Tool action:', data.content);
      break;
    case 'done':
      console.log('Conversation completed');
      break;
    case 'error':
      console.error('Error:', data.message);
      break;
  }
};
```

## 工具说明

### 可用工具

| 工具名称 | 功能描述 | 参数说明 |
|---------|---------|----------|
| retrieve_profile | 用于了解用户信息、自身身份或行为准则 | 无 |
| get_current_time | 获取当前时间 | 无 |
| web_search | 网页搜索引擎，用于获取时事、事实等信息 | 搜索关键词 |
| get_weather | 获取指定城市的天气情况 | 城市名称（支持中文和英文） |
| hot_search | 获取各平台热搜数据 | 平台名称（weibo/douyin/kuaishou/baidu/thepaper/toutiao） |
| safe_shell | 执行安全的shell命令 | 命令字符串 |
| history_search | 搜索历史对话内容 | 搜索关键词 |

## 依赖说明

### 后端依赖

- Python 3.8+
- langchain-openai - 用于与OpenAI API交互
- langchain-core - LangChain核心功能
- langchain-classic - LangChain经典组件
- langchain-text-splitters - 文本分割工具
- langchain-huggingface - HuggingFace模型集成
- langchain-community - LangChain社区组件
- requests - 网络请求
- tavily - 搜索工具
- uvicorn - ASGI服务器
- fastapi - Web框架
- psycopg2-binary - PostgreSQL驱动
- sqlalchemy - ORM框架
- pgvector - PostgreSQL向量扩展
- numpy - 数值计算库
- sentence-transformers - 嵌入模型
- torch - PyTorch深度学习框架
- redis - Redis客户端

### 前端依赖

- Vue 3 - 前端框架
- TypeScript - 类型系统
- Vite - 构建工具
- Vue DevTools - 开发工具

## 注意事项

1. 确保您的API密钥和服务地址正确配置
2. 某些工具可能需要网络连接
3. 工具调用过程会在控制台显示，可根据需要在代码中调整
4. 首次运行时会下载嵌入模型，可能需要一些时间
5. 对话历史会存储在向量数据库中，具体存储位置取决于数据库配置
6. 使用Ollama模式时，确保Ollama服务已启动且模型已下载

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request，一起完善这个项目！
