# PyAi - 智能AI代理系统

PyAi是一个基于LangChain的智能AI代理系统，能够通过工具调用增强大语言模型的能力，支持多种实用功能，并使用向量数据库存储对话历史。现在已升级为FastAPI应用，提供API接口服务，并配备了Vue前端界面。

## 项目功能

- 🤖 **智能对话**：基于OpenAI API的多轮对话能力
- 📅 **时间查询**：获取当前时间信息
- 🔍 **网络搜索**：进行网页搜索和获取热搜数据
- ☁️ **天气查询**：获取指定城市的天气情况
- 👤 **用户信息**：检索用户资料和身份信息
- 📚 **对话历史管理**：使用向量数据库存储和管理对话历史
- 🔎 **语义相似性检索**：基于语义相似性检索历史消息
- 🚀 **API接口**：提供FastAPI接口，支持流式响应
- 💻 **前端界面**：基于Vue 3的现代化前端界面
- 🔧 **安全 shell**：执行安全的shell命令
- 🔍 **历史搜索**：搜索历史对话内容

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
├── tools/             # 工具实现
│   ├── current_time.py    # 获取当前时间
│   ├── history_search.py  # 搜索历史对话
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
│   └── time_trial.py      # 时间测试工具
├── web/               # 前端界面
│   ├── public/        # 静态资源
│   ├── src/           # 源代码
│   │   ├── utils/     # 工具函数
│   │   ├── views/     # 页面组件
│   │   ├── App.vue    # 应用入口
│   │   └── main.ts    # 主文件
│   ├── package.json   # 前端依赖
│   └── vite.config.ts # Vite配置
├── .env.example       # 环境变量示例
├── .gitignore         # Git忽略文件
├── README.md          # 项目说明
├── init_db.sql        # 数据库初始化脚本
├── main.py            # 主入口文件（FastAPI应用）
└── requirements.txt   # 项目依赖
```

## 快速开始

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

4. 配置环境变量：
   - 复制 `.env.example` 文件为 `.env`
   - 编辑 `.env` 文件，填写以下信息：
     ```
     API_KEY=your_api_key
     API_URL=your_api_url
     API_MODEL=your_api_model
     API_TIMEOUT=60
     MODEL_PATH=your_embedding_model_path  # 例如：sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
     DEVICE=cpu  # 可选：cuda（如果有GPU）
     NORMALIZE_EMBEDDINGS=True
     ```

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

## 新增功能说明

### 对话历史管理

项目使用向量数据库存储对话历史，具有以下特点：

- 自动存储每轮对话的用户输入和AI回复
- 支持按时间顺序获取历史消息
- 支持清空指定会话的历史消息
- 基于语义相似性检索历史消息

### 多轮对话支持

系统会自动管理对话历史，确保对话的连贯性和上下文理解。

### 流式响应

API接口支持流式响应，实时返回AI的回复内容，提升用户体验。

## 自定义扩展

### 添加新工具

1. 在 `tools/` 目录下创建新的工具文件
2. 在 `tools/tool_list.py` 中注册新工具
3. 确保工具函数能够正确处理输入参数并返回有用的结果

### 自定义系统提示

修改 `util/agent.py` 中的 `system_message` 模板，定制AI的行为和角色。

### 调整对话历史管理

修改 `util/DbChatMessageHistory.py` 中的相关方法，调整对话历史的存储和检索行为。

## 依赖说明

### 后端依赖

- Python 3.8+
- langchain-openai - 用于与OpenAI API交互
- langchain-core - LangChain核心功能
- langchain-classic - LangChain经典组件
- langchain-text-splitters - 文本分割工具
- langchain-huggingface - HuggingFace模型集成
- langchain-community - LangChain社区组件
- python-dotenv - 环境变量管理
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

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request，一起完善这个项目！