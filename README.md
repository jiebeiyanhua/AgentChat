# PyAi - 智能AI代理系统

PyAi是一个基于LangChain的智能AI代理系统，能够通过工具调用增强大语言模型的能力，支持多种实用功能，并使用向量数据库存储对话历史。现在已升级为FastAPI应用，提供API接口服务。

## 项目功能

- 🤖 **智能对话**：基于OpenAI API的多轮对话能力
- 📅 **时间查询**：获取当前时间信息
- 🔍 **网络搜索**：进行网页搜索和获取热搜数据
- ☁️ **天气查询**：获取指定城市的天气情况
- 👤 **用户信息**：检索用户资料和身份信息
- 📚 **对话历史管理**：使用向量数据库存储和管理对话历史
- 🔎 **语义相似性检索**：基于语义相似性检索历史消息
- 🚀 **API接口**：提供FastAPI接口，支持流式响应

## 项目结构

```
PyAi/
├── definition/        # 定义文件（身份、记忆等）
│   ├── IDENTITY.md
│   ├── MEMORY.md
│   ├── SOUL-example.md
│   └── USER-example.md
├── tools/             # 工具实现
│   ├── current_time.py  # 获取当前时间
│   ├── prmpot.py        # 检索用户资料
│   ├── search.py        # 网页搜索和热搜
│   ├── tool_executor.py # 工具执行器
│   ├── tool_list.py     # 工具列表管理
│   └── weather.py       # 获取天气信息
├── util/              # 工具类
│   ├── DbChatMessageHistory.py # 对话历史管理
│   ├── agent.py           # 核心Agent实现
│   ├── db_models.py       # 数据库模型
│   ├── embeddings_models.py # 嵌入模型
│   └── time_trial.py      # 时间测试工具
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

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量：
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

```bash
python main.py
```

服务将在 `http://0.0.0.0:8000` 上运行。

## API接口

### `/agent-talk` POST

**参数**：
- `input_text`：用户输入的问题
- `session_id`：会话ID，用于区分不同的对话会话

**返回**：
- 流式响应（text/event-stream），包含AI的回复内容

**示例请求**：
```bash
curl -X POST "http://localhost:8000/agent-talk" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "input_text=今天天气怎么样？&session_id=user123"
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