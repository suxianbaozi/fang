import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import yaml

@dataclass
class AIModelConfig:
    name: str
    provider: str  # openai, anthropic, ollama, etc.
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model_id: str = ""
    max_tokens: int = 2048
    temperature: float = 0.7

@dataclass
class MCPConfig:
    label: str
    value: str
    description: Optional[str] = None
    enabled: bool = True
    mcp_url: Optional[str] = None  # 外部 MCP URL
    tools: List[Dict[str, Any]] = None  # MCP 支持的工具列表

class Config:
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config_data = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        # 默认配置
        default_config = {
            "ai_models": [
                {
                    "name": "doubao",
                    "provider": "volcengine",
                    "model_id": "ep-20241008144238-4sttw",
                    "api_key": "your_api_key_here",
                    "api_base": "https://ark.cn-beijing.volces.com/api/v3",
                    "max_tokens": 2048,
                    "temperature": 0.7
                }
            ],
            "default_model": "doubao",
            "mcp_options": [
                {
                    "label": "数据查询",
                    "value": "data_query",
                    "description": "企业数据查询和统计功能",
                    "enabled": True,
                    "mcp_url": "http://data.shuidi.cn/mcp/",  # fastmcp 协议格式
                    "tools": []
                },
                {
                    "label": "文件处理",
                    "value": "file_processing", 
                    "description": "文件上传、处理和分析功能",
                    "enabled": False,
                    "mcp_url": "http://localhost:8001/mcp/",
                    "tools": []
                },
                {
                    "label": "代码执行",
                    "value": "code_execution",
                    "description": "代码运行和调试功能",
                    "enabled": False,
                    "mcp_url": "http://localhost:8002/mcp/",
                    "tools": []
                },
                {
                    "label": "网络搜索",
                    "value": "web_search",
                    "description": "实时网络信息搜索功能",
                    "enabled": False,
                    "mcp_url": "http://localhost:8003/mcp/",
                    "tools": []
                },
                {
                    "label": "图像分析",
                    "value": "image_analysis",
                    "description": "图像识别和分析功能",
                    "enabled": False,
                    "mcp_url": "http://localhost:8004/mcp/",
                    "tools": []
                }
            ],
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "cors_origins": ["http://localhost:5173", "http://127.0.0.1:5173"]
            }
        }
        
        # 尝试加载配置文件
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                        file_config = yaml.safe_load(f)
                    else:
                        file_config = json.load(f)
                
                # 合并配置
                return self._merge_config(default_config, file_config)
            except Exception as e:
                print(f"配置文件加载失败，使用默认配置: {e}")
                return default_config
        else:
            # 创建默认配置文件
            self._save_config(default_config)
            return default_config
    
    def _merge_config(self, default: Dict, custom: Dict) -> Dict:
        """合并配置"""
        result = default.copy()
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self, config: Dict[str, Any]):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"配置文件保存失败: {e}")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用的AI模型列表"""
        models = []
        for model_config in self.config_data.get("ai_models", []):
            # 检查API密钥是否配置（从环境变量或配置文件）
            api_key = model_config.get("api_key") or self._get_api_key(model_config.get("provider"))
            models.append({
                "name": model_config.get("name"),
                "provider": model_config.get("provider"),
                "model_id": model_config.get("model_id"),
                "available": api_key is not None or model_config.get("provider") == "ollama"
            })
        return models
    
    def get_default_model(self) -> str:
        """获取默认模型"""
        return self.config_data.get("default_model", "GPT-3.5 Turbo")
    
    def get_model_config(self, model_name: str) -> Optional[AIModelConfig]:
        """获取指定模型的配置"""

        print(444,self.config_data.get("ai_models"))

        for model in self.config_data.get("ai_models", []):
            if model.get("name") == model_name:
                # 从环境变量获取API密钥
                api_key = model.get("api_key") or self._get_api_key(model.get("provider"))
                return AIModelConfig(
                    name=model.get("name"),
                    provider=model.get("provider"),
                    api_key=api_key,
                    api_base=model.get("api_base"),
                    model_id=model.get("model_id"),
                    max_tokens=model.get("max_tokens", 2048),
                    temperature=model.get("temperature", 0.7)
                )
        return None
    
    def get_mcp_options(self) -> List[Dict[str, Any]]:
        """获取MCP选项列表"""
        return [
            mcp for mcp in self.config_data.get("mcp_options", [])
            if mcp.get("enabled", True)
        ]
    
    def get_mcp_config(self, mcp_value: str) -> Optional[MCPConfig]:
        """获取指定MCP的配置"""
        for mcp in self.config_data.get("mcp_options", []):
            if mcp.get("value") == mcp_value:
                return MCPConfig(
                    label=mcp.get("label"),
                    value=mcp.get("value"),
                    description=mcp.get("description"),
                    enabled=mcp.get("enabled", True),
                    mcp_url=mcp.get("mcp_url"),
                    tools=mcp.get("tools", [])
                )
        return None
    
    def _get_api_key(self, provider: str) -> Optional[str]:
        """从环境变量获取API密钥"""
        env_keys = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "azure": "AZURE_OPENAI_KEY"
        }
        return os.getenv(env_keys.get(provider, f"{provider.upper()}_API_KEY"))
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return self.config_data.get("server", {
            "host": "0.0.0.0",
            "port": 8000,
            "cors_origins": ["http://localhost:5173"]
        })
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.config_data = self._merge_config(self.config_data, new_config)
        self._save_config(self.config_data)
    
    def reload_config(self):
        """重新加载配置"""
        self.config_data = self._load_config() 