from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio
import time
from datetime import datetime
from contextlib import asynccontextmanager

from config import Config
from ai_service import AIService
from mcp_service import MCPService

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时的初始化
    print("🚀 AI Chat Backend 启动中...")
    yield
    # 关闭时的清理
    print("🔄 AI Chat Backend 关闭中，清理 MCP 连接...")
    try:
        await mcp_service.disconnect_all_clients()
        print("✅ MCP 客户端连接已清理")
    except Exception as e:
        print(f"❌ 清理 MCP 连接时出错: {e}")

app = FastAPI(
    title="AI Chat Backend", 
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
config = Config()
ai_service = AIService(config)
mcp_service = MCPService(config)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    selected_mcp: List[str] = []
    model: Optional[str] = None

class MCPOption(BaseModel):
    label: str
    value: str
    description: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "AI Chat Backend is running!"}

@app.get("/config")
async def get_config():
    """获取配置信息"""
    return {
        "available_models": config.get_available_models(),
        "default_model": config.get_default_model(),
        "mcp_options": config.get_mcp_options()
    }

@app.get("/mcp/list")
async def get_mcp_list():
    """获取MCP选项列表"""
    return config.get_mcp_options()

@app.get("/mcp/{mcp_value}/tools")
async def get_mcp_tools(mcp_value: str):
    """获取指定MCP的工具列表"""
    try:
        tools = await mcp_service.get_mcp_tools(mcp_value)
        mcp_config = config.get_mcp_config(mcp_value)
        
        return {
            "mcp_value": mcp_value,
            "mcp_config": {
                "label": mcp_config.label if mcp_config else "",
                "description": mcp_config.description if mcp_config else "",
                "mcp_url": mcp_config.mcp_url if mcp_config else None
            },
            "tools": tools,
            "tool_count": len(tools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/{mcp_value}/refresh")
async def refresh_mcp_tools(mcp_value: str):
    """刷新指定MCP的工具缓存"""
    try:
        await mcp_service.refresh_mcp_tools(mcp_value)
        tools = await mcp_service.get_mcp_tools(mcp_value)
        return {
            "message": f"MCP {mcp_value} 工具缓存已刷新",
            "tool_count": len(tools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/{mcp_value}/call")
async def call_mcp_function(mcp_value: str, request: dict):
    """调用指定MCP的函数"""
    try:
        function_name = request.get("function")
        parameters = request.get("parameters", {})
        
        if not function_name:
            raise HTTPException(status_code=400, detail="缺少 function 参数")
        
        result = await mcp_service.execute_mcp_function(mcp_value, function_name, parameters)
        return {
            "mcp_value": mcp_value,
            "function": function_name,
            "parameters": parameters,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """普通聊天接口（非流式）"""
    try:
        # 使用指定模型或默认模型
        model = request.model or config.get_default_model()
        
        # 获取AI响应
        response = await ai_service.get_response(
            messages=request.messages,
            model=model,
            selected_mcp=request.selected_mcp
        )
        
        return {
            "message": response,
            "model_used": model,
            "selected_mcp": request.selected_mcp,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口（支持打字机效果）"""
    try:
        # 使用指定模型或默认模型
        model = request.model or config.get_default_model()
        
        async def generate_response():
            """生成流式响应"""
            # try:
            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'model': model, 'selected_mcp': request.selected_mcp})}\n\n"
            
            # 获取AI流式响应
            async for chunk in ai_service.get_streaming_response(
                messages=request.messages,
                model=model,
                selected_mcp=request.selected_mcp
            ):
                if chunk:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    # 添加小延迟以模拟打字机效果
                    await asyncio.sleep(0.02)
            
            # 发送结束信号
            yield f"data: {json.dumps({'type': 'end', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # except Exception as stream_error:
            #     # 如果流式响应出错，发送错误信息而不是中断
            #     error_msg = f"流式响应出现错误: {str(stream_error)}"
            #     print(f"Stream error: {stream_error}")  # 服务端日志
            #     yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            #     yield f"data: {json.dumps({'type': 'end', 'timestamp': datetime.now().isoformat()})}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ai_service": ai_service.is_healthy(),
            "mcp_service": mcp_service.is_healthy()
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000,reload=True) 