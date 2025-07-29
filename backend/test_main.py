from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="AI Chat Test API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 简单的数据模型
class TestMessage(BaseModel):
    content: str
    role: str = "user"

class TestResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any] = {}

@app.get("/")
async def root():
    """根路径测试"""
    return {"message": "FastAPI 测试服务运行正常", "status": "ok"}

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return TestResponse(
        status="healthy",
        message="服务运行正常",
        data={"timestamp": "2024-01-01", "version": "1.0.0"}
    )

@app.post("/test/echo")
async def echo_test(message: TestMessage):
    """回声测试接口"""
    return TestResponse(
        status="success",
        message=f"收到消息: {message.content}",
        data={"original": message.dict(), "echo": f"Echo: {message.content}"}
    )

@app.get("/test/config")
async def test_config():
    """配置测试接口"""
    return {
        "status": "ok",
        "config": {
            "api_title": "AI Chat Test API",
            "version": "1.0.0",
            "test_mode": True
        }
    }

@app.get("/test/mcp")
async def test_mcp():
    """MCP 测试接口"""
    return {
        "status": "ok",
        "mcp_options": [
            {
                "label": "测试 MCP",
                "value": "test_mcp",
                "description": "用于测试的 MCP 模块",
                "enabled": True
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 