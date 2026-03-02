# PyAi - 智能AI代理系统

PyAi是一个基于LangChain的智能AI代理系统，能够通过工具调用增强大语言模型的能力，支持多种实用功能。

## 项目功能

- 🤖 **智能对话**：基于OpenAI API的多轮对话能力
- 📅 **时间查询**：获取当前时间信息
- 🔍 **网络搜索**：进行网页搜索和获取热搜数据
- ☁️ **天气查询**：获取指定城市的天气情况
- 👤 **用户信息**：检索用户资料和身份信息

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

## 示例对话

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
```

## 自定义扩展

### 添加新工具

1. 在 `tools/` 目录下创建新的工具文件
2. 在 `tools/tool_list.py` 中注册新工具
3. 确保工具函数能够正确处理输入参数并返回有用的结果

### 自定义系统提示

修改 `agent.py` 中的 `system_message` 模板，定制AI的行为和角色。

## 依赖说明

- Python 3.8+
- langchain-openai - 用于与OpenAI API交互
- langchain-core - LangChain核心功能
- langchain-classic - LangChain经典组件
- python-dotenv - 环境变量管理
- requests - 网络请求

## 注意事项

1. 确保您的API密钥和服务地址正确配置
2. 某些工具可能需要网络连接
3. 工具调用过程会在控制台显示，可根据需要在代码中调整

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request，一起完善这个项目！