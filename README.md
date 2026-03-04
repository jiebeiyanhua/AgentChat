# PyAi - 智能AI代理系统

PyAi是一个基于LangChain的智能AI代理系统，能够通过工具调用增强大语言模型的能力，支持多种实用功能，并使用向量数据库存储对话历史。

## 项目功能

- 🤖 **智能对话**：基于OpenAI API的多轮对话能力
- 📅 **时间查询**：获取当前时间信息
- 🔍 **网络搜索**：进行网页搜索和获取热搜数据
- ☁️ **天气查询**：获取指定城市的天气情况
- 👤 **用户信息**：检索用户资料和身份信息
- 📚 **对话历史管理**：使用向量数据库存储和管理对话历史
- 🔎 **语义相似性检索**：基于语义相似性检索历史消息

## 项目结构

```
PyAi/
├── definition/        # 定义文件（身份、记忆等）
├── tools/             # 工具实现
│   ├── current_time.py  # 获取当前时间
│   ├── prmpot.py        # 检索用户资料
│   ├── search.py        # 网页搜索和热搜
│   ├── tool_executor.py # 工具执行器
│   ├── tool_list.py     # 工具列表管理
│   └── weather.py       # 获取天气信息
├── util/              # 工具类
│   └── DbChatMessageHistory.py # 对话历史管理（基于Chroma向量数据库）
├── .env.example       # 环境变量示例
├── .gitignore         # Git忽略文件
├── agent.py           # 核心Agent实现
├── main.py            # 主入口文件
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

然后在命令行中输入问题，AI会进行回复。输入 `exit` 退出程序。

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

项目使用 Chroma 向量数据库存储对话历史，具有以下特点：

- 自动存储每轮对话的用户输入和AI回复
- 支持按时间顺序获取历史消息
- 支持清空指定会话的历史消息
- 基于语义相似性检索历史消息

### 多轮对话支持

系统会自动管理对话历史，默认保存最近5轮对话（10条消息），确保对话的连贯性和上下文理解。

## 操作步骤

### 基本使用

1. **启动系统**：运行 `python main.py` 启动系统
2. **输入问题**：在命令行中输入您的问题，按回车发送
3. **查看回复**：AI会分析问题并生成回复，可能会调用工具获取额外信息
4. **继续对话**：可以继续输入新的问题，系统会保持对话上下文
5. **退出系统**：输入 `exit` 退出程序

### 示例对话

```
==============================
用户：
今天天气怎么样？
--- 调用LLM ---
[工具调用] [{'name': 'get_weather', 'args': {'city': '北京'}}]
AI: 北京市今天的天气情况如下：
- 天气：晴
- 温度：25°C
- 湿度：45%
- 风力：3级
- 空气质量：良

==============================
用户：
现在几点了？
--- 调用LLM ---
[工具调用] [{'name': 'get_current_time', 'args': {}}]
AI: 现在的时间是2026年3月2日 14:30:45

==============================
用户：
最近有什么热点新闻？
--- 调用LLM ---
[工具调用] [{'name': 'hot_search', 'args': {'platform': 'weibo'}}]
AI: 以下是新浪微博的热搜榜单：
1. #XXX#
2. #XXX#
3. #XXX#
...

==============================
用户：
exit
```

### 高级功能

#### 语义相似性检索

系统内部使用语义相似性检索来增强对话理解，您可以通过修改 `DbChatMessageHistory.py` 中的 `search_similar` 方法来自定义检索行为。

#### 自定义会话管理

每个会话都有唯一的会话ID，系统会为每个会话创建独立的对话历史存储。您可以通过修改 `main.py` 中的会话ID生成逻辑来自定义会话管理。

## 自定义扩展

### 添加新工具

1. 在 `tools/` 目录下创建新的工具文件
2. 在 `tools/tool_list.py` 中注册新工具
3. 确保工具函数能够正确处理输入参数并返回有用的结果

### 自定义系统提示

修改 `agent.py` 中的 `system_message` 模板，定制AI的行为和角色。

### 调整对话历史管理

修改 `agent.py` 中的 `max_turns` 参数，调整保存的对话轮数：

```python
max_turns = 5  # 可以根据需要调整
max_messages = max_turns * 2  # 每轮包含用户和AI两条消息
```

## 依赖说明

- Python 3.8+
- langchain-openai - 用于与OpenAI API交互
- langchain-core - LangChain核心功能
- langchain-classic - LangChain经典组件
- langchain-chroma - Chroma向量数据库集成
- langchain-huggingface - HuggingFace模型集成
- python-dotenv - 环境变量管理
- requests - 网络请求

## 注意事项

1. 确保您的API密钥和服务地址正确配置
2. 某些工具可能需要网络连接
3. 工具调用过程会在控制台显示，可根据需要在代码中调整
4. 首次运行时会下载嵌入模型，可能需要一些时间
5. 对话历史会存储在 `./chroma_db` 目录中，如需清除所有历史数据可删除该目录

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request，一起完善这个项目！