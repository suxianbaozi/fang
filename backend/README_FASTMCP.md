# FastMCP 集成说明

## 🔧 功能特性

本系统现在支持使用 `fastmcp` 客户端来与 MCP (Model Context Protocol) 服务进行通信，提供了更标准化和高效的 MCP 集成方式。

## 📦 安装依赖

```bash
pip install fastmcp
```

## 🚀 配置说明

### 1. MCP URL 格式

在 `config.yaml` 或配置文件中，MCP URL 现在支持两种格式：

```yaml
mcp_options:
  - label: "数据查询"
    value: "data_query"
    description: "企业数据查询和统计功能"
    enabled: true
    mcp_url: "mcp://data.shuidi.cn:8000"  # FastMCP 协议格式
    tools: []
  
  - label: "文件处理"
    value: "file_processing"
    description: "文件处理功能"
    enabled: false
    mcp_url: "http://localhost:8001/mcp/"  # HTTP 备选格式
    tools: []
```

### 2. 协议支持

- **主要方式**: FastMCP 协议 (`mcp://host:port`)
- **备选方式**: HTTP 协议 (`http://host:port/path`)

系统会自动检测并使用最合适的连接方式。

## 🔄 工作流程

### 1. 工具发现

系统会尝试以下方法获取 MCP 工具列表：

```python
# FastMCP 方式 (优先)
tools = await client.list_tools()
tools = await client.get_tools()
tools = await client.tools()
tools = await client.send_request("tools/list", {})

# HTTP 备选方式
GET http://mcp_url/tools
```

### 2. 函数调用

系统会尝试以下方法执行 MCP 函数：

```python
# FastMCP 方式 (优先)
result = await client.call_tool(function_name, parameters)
result = await client.invoke_tool(function_name, parameters)
result = await client.execute_tool(function_name, parameters)
result = await client.send_request("tools/call", {"name": function_name, "arguments": parameters})

# HTTP 备选方式
POST http://mcp_url/call
```

## 🛠️ MCP 服务要求

### FastMCP 服务端

你的 MCP 服务需要实现标准的 MCP 协议接口：

1. **工具列表接口**：
   - 方法: `list_tools()` 或 `get_tools()`
   - 返回格式:
   ```json
   [
     {
       "name": "function_name",
       "description": "功能描述",
       "inputSchema": {
         "type": "object",
         "properties": {...}
       }
     }
   ]
   ```

2. **工具调用接口**：
   - 方法: `call_tool(name, arguments)` 或 `invoke_tool(name, arguments)`
   - 参数: 函数名和参数字典
   - 返回: 执行结果

### HTTP 备选接口

如果使用 HTTP 备选方式，需要提供：

1. **GET /tools** - 获取工具列表
2. **POST /call** - 执行函数调用
   ```json
   {
     "function": "function_name",
     "parameters": {...}
   }
   ```

## 🔍 调试和日志

系统会输出详细的调试信息：

```
创建 FastMCP 客户端成功: mcp://data.shuidi.cn:8000
使用 list_tools 获取工具成功
fastmcp tools: [...]
使用 call_tool 调用成功
FastMCP 调用结果: {...}
```

## 🚨 错误处理

- **连接失败**: 自动降级到 HTTP 方式
- **方法不存在**: 尝试多种标准方法名
- **调用超时**: 30秒超时保护
- **资源清理**: 应用关闭时自动断开所有连接

## 📝 最佳实践

1. **优先使用 FastMCP 协议** (`mcp://`) 以获得最佳性能
2. **提供 HTTP 备选接口** 以确保兼容性
3. **实现标准方法名** (`list_tools`, `call_tool`) 以获得最佳兼容性
4. **合理设置超时时间** 避免长时间阻塞
5. **提供详细的工具描述** 帮助 AI 更好地理解和使用工具

## 🔧 故障排除

### 1. 连接问题
```
创建 FastMCP 客户端失败: Connection refused
```
- 检查 MCP 服务是否启动
- 确认端口号是否正确
- 验证网络连接

### 2. 方法调用问题
```
尝试 list_tools 方法失败: AttributeError
```
- 检查 FastMCP 版本兼容性
- 确认服务端实现了标准接口
- 查看服务端支持的方法列表

### 3. 数据格式问题
```
FastMCP 获取工具失败: KeyError: 'name'
```
- 确认返回数据格式符合 MCP 标准
- 检查字段名称 (`inputSchema` vs `input_schema`)
- 验证数据类型正确性 