import asyncio
import json
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import asdict

try:
    from fastmcp import Client
except ImportError:
    print("警告: fastmcp 未安装，将使用 HTTP 客户端作为备选方案")
    Client = None

from config import Config, MCPConfig

class MCPService:
    def __init__(self, config: Config):
        self.config = config
        self._external_mcp_cache = {}
        self._mcp_clients = {}  # 缓存 fastmcp 客户端
    
    async def get_mcp_tools(self, mcp_value: str) -> List[Dict[str, Any]]:
        """获取MCP支持的工具列表"""
        mcp_config = self.config.get_mcp_config(mcp_value)

        print("mcp_config", mcp_config)
        if not mcp_config:
            return []
        
        # 使用 fastmcp 客户端获取工具列表
        if mcp_config.mcp_url:
            return await self._get_external_mcp_tools(mcp_config)
        else:
            print(f"警告: MCP {mcp_value} 没有配置 mcp_url")
            return []
    
    async def _get_fastmcp_client(self, mcp_config: MCPConfig) -> Optional[Client]:
        """获取或创建 fastmcp 客户端"""
        if Client is None:
            return None
            
        client_key = f"client_{mcp_config.value}"
        
        if client_key not in self._mcp_clients:
            try:
                # 创建 fastmcp 客户端，直接使用 URL
                client = Client(mcp_config.mcp_url)
                self._mcp_clients[client_key] = client
                print(f"创建 FastMCP 客户端成功: {mcp_config.mcp_url}")
                return client
            except Exception as e:
                print(f"创建 FastMCP 客户端失败 {mcp_config.mcp_url}: {e}")
                return None
        
        return self._mcp_clients.get(client_key)
    
    async def _get_external_mcp_tools(self, mcp_config: MCPConfig) -> List[Dict[str, Any]]:
        """使用 fastmcp 客户端从外部 MCP 获取工具列表"""
        cache_key = f"tools_{mcp_config.value}"
        
        # 使用缓存避免频繁请求
        if cache_key in self._external_mcp_cache:
            return self._external_mcp_cache[cache_key]

        print("mcp_config.mcp_url111", mcp_config.mcp_url)

        # 尝试使用 fastmcp 客户端
        client = await self._get_fastmcp_client(mcp_config)
        if client:
            try:
                # 使用 fastmcp 的上下文管理器和 list_tools 方法
                async with client:
                    tools_response = await client.list_tools()
                    
                    # 提取工具列表
                    tools = tools_response.tools if hasattr(tools_response, 'tools') else tools_response
                    
                    # 转换为标准格式
                    formatted_tools = []
                    for tool in tools:
                        # 处理不同类型的工具对象
                        if hasattr(tool, 'name'):
                            # FastMCP Tool 对象
                            formatted_tool = {
                                "name": tool.name,
                                "description": tool.description or "",
                                "parameters": tool.inputSchema or {}
                            }
                        elif isinstance(tool, dict):
                            # 字典格式
                            formatted_tool = {
                                "name": tool.get("name", ""),
                                "description": tool.get("description", ""),
                                "parameters": tool.get("inputSchema", tool.get("input_schema", {}))
                            }
                        else:
                            # 其他格式，尝试转换
                            formatted_tool = {
                                "name": str(getattr(tool, 'name', 'unknown')),
                                "description": str(getattr(tool, 'description', '')),
                                "parameters": getattr(tool, 'inputSchema', getattr(tool, 'input_schema', {}))
                            }
                        
                        formatted_tools.append(formatted_tool)
                    
                    print("formatted tools:", formatted_tools)
                    self._external_mcp_cache[cache_key] = formatted_tools
                    return formatted_tools
            except Exception as e:
                print(f"FastMCP 获取工具失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 备选方案：使用 HTTP 客户端
        return await self._get_external_mcp_tools_http(mcp_config, cache_key)
    
    async def _get_external_mcp_tools_http(self, mcp_config: MCPConfig, cache_key: str) -> List[Dict[str, Any]]:
        """HTTP 备选方案获取工具列表"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 标准 MCP 工具发现接口
                response = await client.get(f"{mcp_config.mcp_url}/tools")
                if response.status_code == 200:
                    tools = response.json().get("tools", [])
                    self._external_mcp_cache[cache_key] = tools
                    return tools
        except Exception as e:
            
            print(f"HTTP 获取外部 MCP 工具失败 {mcp_config.mcp_url}: {e}")
        
        return []
    
    async def execute_mcp_function(self, mcp_value: str, function_name: str, parameters: Dict[str, Any]) -> Any:
        """使用 fastmcp 执行MCP函数"""
        mcp_config = self.config.get_mcp_config(mcp_value)
        if not mcp_config:
            raise ValueError(f"未找到MCP模块: {mcp_value}")
        
        if mcp_config.mcp_url:
            return await self._call_external_mcp(mcp_config, function_name, parameters)
        else:
            raise ValueError(f"MCP {mcp_value} 没有配置 mcp_url，无法执行函数调用")
    
    async def _call_external_mcp(self, mcp_config: MCPConfig, function_name: str, parameters: Dict[str, Any]) -> Any:
        """使用 fastmcp 客户端调用外部 MCP 函数"""
        # 尝试使用 fastmcp 客户端
        client = await self._get_fastmcp_client(mcp_config)
        if client:
            try:
                # 使用 fastmcp 的上下文管理器和 call_tool 方法
                async with client:
                    result = await client.call_tool(function_name, parameters)
                    print(f"FastMCP 原始调用结果: {result}")
                    
                    # 处理返回结果
                    if hasattr(result, 'content'):
                        # 如果是 MCP 响应对象，提取内容
                        content = result.content
                        if len(content) > 0:
                            text_content = content[0].text if hasattr(content[0], 'text') else str(content[0])
                            print(f"提取的文本内容: {text_content}")
                            
                            # 尝试解析为 JSON
                            try:
                                import json
                                parsed_result = json.loads(text_content)
                                print(f"解析的 JSON 结果: {parsed_result}")
                                return parsed_result
                            except json.JSONDecodeError:
                                # 如果不是 JSON，返回原始文本
                                print("不是有效的 JSON，返回原始文本")
                                return text_content
                        return str(result)
                    else:
                        # 直接返回结果
                        print(f"直接返回结果: {result}")
                        return result
            except Exception as e:
                print(f"FastMCP 调用失败: {e}")
        
        # 备选方案：使用 HTTP 调用
        return await self._call_external_mcp_http(mcp_config, function_name, parameters)
    
    async def _call_external_mcp_http(self, mcp_config: MCPConfig, function_name: str, parameters: Dict[str, Any]) -> Any:
        """HTTP 备选方案调用外部 MCP 函数"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "function": function_name,
                    "parameters": parameters
                }
                response = await client.post(f"{mcp_config.mcp_url}/call", json=payload)
                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"外部 MCP 调用失败: {response.status_code} - {response.text}")
        except Exception as e:
            raise Exception(f"外部 MCP 调用异常: {str(e)}")
    
    async def refresh_mcp_tools(self, mcp_value: str):
        """刷新 MCP 工具缓存"""
        cache_key = f"tools_{mcp_value}"
        if cache_key in self._external_mcp_cache:
            del self._external_mcp_cache[cache_key]
        
        # 同时刷新客户端连接
        client_key = f"client_{mcp_value}"
        if client_key in self._mcp_clients:
            try:
                client = self._mcp_clients[client_key]
                # fastmcp 客户端会在上下文管理器退出时自动关闭
                print(f"刷新 FastMCP 客户端: {client_key}")
            except Exception as e:
                print(f"刷新 FastMCP 客户端失败: {e}")
            del self._mcp_clients[client_key]
    
    async def disconnect_all_clients(self):
        """断开所有 MCP 客户端连接"""
        for client_key, client in list(self._mcp_clients.items()):
            try:
                # fastmcp 客户端使用上下文管理器，不需要手动断开
                print(f"清理 FastMCP 客户端: {client_key}")
            except Exception as e:
                print(f"清理 FastMCP 客户端失败 {client_key}: {e}")
        self._mcp_clients.clear()
    
    def is_healthy(self) -> bool:
        """检查MCP服务健康状态"""
        try:
            # 检查配置的MCP选项是否都有 mcp_url
            mcp_options = self.config.get_mcp_options()
            for option in mcp_options:
                if not option.get("mcp_url"):
                    return False
            return True
        except Exception:
            return False 