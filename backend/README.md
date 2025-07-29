# AI Chat Backend

基于 FastAPI 的 AI 聊天后端服务，支持多种 AI 模型、MCP 功能集成和流式响应。

## 功能特点

- 🤖 **多AI模型支持**: OpenAI GPT、Anthropic Claude、Ollama 本地模型等
- 🔌 **MCP集成**: 支持多种 MCP (Model Context Protocol) 功能模块
- 💬 **流式响应**: 支持打字机效果的实时流式对话
- ⚙️ **灵活配置**: 支持 YAML/JSON 配置文件和环境变量
- 🌐 **RESTful API**: 完整的 REST API 接口
- 📊 **健康检查**: 内置服务健康状态监控

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量示例文件：

```bash
cp env.example .env
```

编辑 `.env` 文件，添加你的 API 密钥：

```bash
# OpenAI API 密钥
OPENAI_API_KEY=sk-your-openai-key-here

# Anthropic API 密钥  
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
```

### 3. 启动服务

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后，访问 http://localhost:8000 查看API文档。

## API 接口

### 基础接口

- `GET /` - 服务状态
- `GET /config` - 获取配置信息
- `GET /health` - 健康检查
- `GET /mcp/list` - 获取MCP选项列表

### 聊天接口

- `POST /chat` - 普通聊天（非流式）
- `POST /chat/stream` - 流式聊天（支持打字机效果）

#### 请求格式

```json
{
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "selected_mcp": ["data_query", "web_search"],
  "model": "GPT-3.5 Turbo"
}
```

#### 流式响应格式

```
data: {"type": "start", "model": "GPT-3.5 Turbo", "selected_mcp": ["data_query"]}

data: {"type": "chunk", "content": "你好"}

data: {"type": "chunk", "content": "！"}

data: {"type": "end", "timestamp": "2023-12-07T10:30:00"}
```

## 配置文件

系统会自动生成 `config.yaml` 配置文件，你可以根据需要修改：

### AI 模型配置

```yaml
ai_models:
  - name: "GPT-4"
    provider: "openai"
    model_id: "gpt-4"
    max_tokens: 2048
    temperature: 0.7
  - name: "Claude-3 Sonnet"
    provider: "anthropic"
    model_id: "claude-3-sonnet-20240229"
    max_tokens: 2048
    temperature: 0.7
```

### MCP 选项配置

```yaml
mcp_options:
  - label: "数据查询"
    value: "data_query"
    description: "企业数据查询和统计功能"
    enabled: true
  - label: "文件处理"
    value: "file_processing"
    description: "文件上传、处理和分析功能"
    enabled: true
```

## MCP 模块

当前支持的 MCP 模块：

- **data_query**: 数据查询功能
- **file_processing**: 文件处理功能
- **code_execution**: 代码执行功能
- **web_search**: 网络搜索功能
- **image_analysis**: 图像分析功能

### 扩展 MCP 模块

要添加新的 MCP 模块：

1. 在 `mcp_service.py` 中创建新的 MCP 类
2. 继承 `BaseMCP` 基类
3. 实现 `get_available_functions()` 方法
4. 在 `MCPService` 中注册新模块

```python
class CustomMCP(BaseMCP):
    def get_available_functions(self):
        return [
            {
                "name": "custom_function",
                "description": "自定义功能",
                "parameters": {...}
            }
        ]
    
    async def custom_function(self, param1: str) -> Dict[str, Any]:
        return {"result": "custom result"}
```

## 开发

### 项目结构

```
backend/
├── main.py              # FastAPI 主应用
├── config.py            # 配置管理
├── ai_service.py        # AI 服务
├── mcp_service.py       # MCP 服务
├── requirements.txt     # Python 依赖
├── config.yaml         # 配置文件（自动生成）
└── README.md           # 说明文档
```

### 添加新的 AI 提供商

1. 在 `ai_service.py` 中添加新的客户端创建逻辑
2. 实现对应的响应和流式响应方法
3. 在配置文件中添加模型配置

## 部署

### Docker 部署

```bash
# 构建镜像
docker build -t ai-chat-backend .

# 运行容器
docker run -p 8000:8000 -e OPENAI_API_KEY=your-key ai-chat-backend
```

### 生产环境

```bash
# 安装生产服务器
pip install gunicorn

# 启动生产服务
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 故障排除

1. **API 密钥问题**: 确保在 `.env` 文件或环境变量中正确配置了 API 密钥
2. **端口冲突**: 修改配置文件中的端口设置
3. **依赖问题**: 使用 `pip install -r requirements.txt` 重新安装依赖
4. **CORS 问题**: 检查 `main.py` 中的 CORS 配置

## 许可证

MIT License 