import asyncio
import json
from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import asdict
import httpx
import openai
from anthropic import AsyncAnthropic

from config import Config, AIModelConfig

class AIService:
    def __init__(self, config: Config):
        self.config = config
        self._clients = {}
    
    def _get_client(self, model_config: AIModelConfig):
        """获取或创建AI客户端"""
        cache_key = f"{model_config.provider}_{model_config.name}"
        
        if cache_key not in self._clients:
            if model_config.provider == "volcengine":
                self._clients[cache_key] = openai.AsyncOpenAI(
                    api_key=model_config.api_key,
                    base_url=model_config.api_base
                )
            elif model_config.provider == "anthropic":
                self._clients[cache_key] = AsyncAnthropic(
                    api_key=model_config.api_key
                )
            elif model_config.provider == "ollama":
                self._clients[cache_key] = httpx.AsyncClient(
                    base_url=model_config.api_base or "http://localhost:11434"
                )
        
        return self._clients[cache_key]
    
    async def get_response(self, messages: List[Dict], model: str, selected_mcp: List[str] = None) -> str:
        """获取AI响应（非流式）"""
        model_config = self.config.get_model_config(model)
        print(111,model_config)
        if not model_config:
            raise ValueError(f"未找到模型配置: {model}")
        
        # 处理MCP上下文
        enhanced_messages = await self._enhance_messages_with_mcp(messages, selected_mcp)
        
        if model_config.provider == "volcengine":
            return await self._get_openai_response(model_config, enhanced_messages)
        elif model_config.provider == "anthropic":
            return await self._get_anthropic_response(model_config, enhanced_messages)
        elif model_config.provider == "ollama":
            return await self._get_ollama_response(model_config, enhanced_messages)
        else:
            raise ValueError(f"不支持的模型提供商: {model_config.provider}")
    
    async def get_streaming_response(self, messages: List[Dict], model: str, selected_mcp: List[str] = None) -> AsyncGenerator[str, None]:
        """获取AI流式响应"""
        model_config = self.config.get_model_config(model)
        if not model_config:
            raise ValueError(f"未找到模型配置: {model}")
        
        # 处理MCP上下文
        enhanced_messages = await self._enhance_messages_with_mcp(messages, selected_mcp)
        
        # 收集完整响应用于函数调用检测
        full_response = ""
        
        if model_config.provider == "volcengine":
            async for chunk in self._get_openai_streaming_response(model_config, enhanced_messages):
                if chunk:
                    full_response += chunk
                    yield chunk
        elif model_config.provider == "anthropic":
            async for chunk in self._get_anthropic_streaming_response(model_config, enhanced_messages):
                if chunk:
                    full_response += chunk
                    yield chunk
        elif model_config.provider == "ollama":
            async for chunk in self._get_ollama_streaming_response(model_config, enhanced_messages):
                if chunk:
                    full_response += chunk
                    yield chunk
        else:
            raise ValueError(f"不支持的模型提供商: {model_config.provider}")
        
        # 检查并处理函数调用
        if self._contains_function_call(full_response):
            async for function_result in self._execute_function_calls(full_response, selected_mcp):
                yield function_result
    
    def _contains_function_call(self, text: str) -> bool:
        """检查文本是否包含函数调用"""
        return "<|FunctionCallBegin|>" in text and "<|FunctionCallEnd|>" in text
    
    async def _execute_function_calls(self, text: str, selected_mcp: List[str]) -> AsyncGenerator[str, None]:
        """执行函数调用并返回结果"""
        import re
        import json
        
        # 提取函数调用内容
        pattern = r'<\|FunctionCallBegin\|\>(.*?)<\|FunctionCallEnd\|\>'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if not matches:
            return
        
        try:
            # 导入MCP服务
            from mcp_service import MCPService
            mcp_service = MCPService(self.config)
            
            yield "\n\n---\n\n🔧 **正在执行MCP工具调用...**\n\n"
            
            function_results = []  # 收集所有函数调用结果
            
            for match in matches:
                try:
                    # 解析JSON格式的函数调用
                    function_calls = json.loads(match.strip())
                    if not isinstance(function_calls, list):
                        function_calls = [function_calls]
                    
                    for call in function_calls:
                        function_name = call.get("name")
                        parameters = call.get("parameters", {})
                        
                        yield f"📞 **调用mcp**: `{function_name}`\n"
                        yield f"📋 **参数**:\n```json\n{json.dumps(parameters, ensure_ascii=False, indent=2)}\n```\n\n"
                        
                        # 执行函数调用
                        try:
                            result = await self._call_mcp_function(
                                function_name, parameters, selected_mcp, mcp_service
                            )
                            
                            if result:
                                # 显示格式化的结果
                                if isinstance(result, dict):
                                    yield f"✅ **执行成功**\n\n"
                                    yield await self._format_mcp_result(result, function_name)
                                elif isinstance(result, list):
                                    yield f"✅ **执行成功** (返回 {len(result)} 条记录)\n\n"
                                    yield await self._format_mcp_result(result, function_name)
                                elif isinstance(result, str):
                                    # 尝试解析字符串为 JSON
                                    try:
                                        parsed_result = json.loads(result)
                                        yield f"✅ **执行成功**\n\n"
                                        yield await self._format_mcp_result(parsed_result, function_name)
                                        result = parsed_result  # 使用解析后的结果
                                    except json.JSONDecodeError:
                                        # 如果不是 JSON，直接显示文本
                                        yield f"✅ **执行结果**:\n{result}\n\n"
                                else:
                                    yield f"✅ **执行结果**:\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n\n"
                                
                                # 收集结果用于后续 AI 处理
                                function_results.append({
                                    "function_name": function_name,
                                    "parameters": parameters,
                                    "result": result
                                })
                            else:
                                yield f"❌ **执行失败**: 未找到匹配的MCP函数\n\n"
                        
                        except Exception as e:
                            yield f"❌ **执行错误**: {str(e)}\n\n"
                
                except json.JSONDecodeError as e:
                    yield f"❌ **JSON解析错误**: {str(e)}\n\n"
                except Exception as e:
                    yield f"❌ **函数调用处理错误**: {str(e)}\n\n"
            
            # 如果有函数调用结果，让 AI 基于结果生成自然语言回答
            if function_results:
                yield "\n\n---\n\n🤖 **AI 分析结果...**\n\n"
                
                # 构建包含函数调用结果的提示
                ai_prompt = self._build_analysis_prompt(function_results)
                
                # 调用 AI 生成基于结果的回答
                async for analysis_chunk in self._get_ai_analysis(ai_prompt):
                    yield analysis_chunk
        
        except Exception as e:
            yield f"❌ **函数调用系统错误**: {str(e)}\n\n"
    
    def _build_analysis_prompt(self, function_results: list) -> str:
        """构建用于 AI 分析的提示"""
        import json
        
        prompt = """请基于以下函数调用结果，用自然语言为用户生成一个清晰、有用的回答。请：

1. 总结主要发现
2. 提供有价值的洞察
3. 如果是查询结果，突出关键信息
4. 用友好、专业的语言表达
5. 不要重复显示原始数据，而是进行分析和解释

函数调用结果：

"""
        
        for i, func_result in enumerate(function_results, 1):
            prompt += f"## 调用 {i}: {func_result['function_name']}\n"
            prompt += f"参数: {json.dumps(func_result['parameters'], ensure_ascii=False)}\n"
            prompt += f"结果: {json.dumps(func_result['result'], ensure_ascii=False, indent=2)}\n\n"
        
        prompt += """
请基于以上结果生成一个专业、有用的回答。
"""
        return prompt
    
    async def _get_ai_analysis(self, prompt: str) -> AsyncGenerator[str, None]:
        """让 AI 分析函数调用结果并生成自然语言回答"""
        try:
            # 使用当前配置的默认模型
            default_model = self.config.get_default_model()
            model_config = self.config.get_model_config(default_model)
            
            if not model_config:
                yield "⚠️ 无法获取 AI 模型配置，无法生成分析\n"
                return
            
            # 构建分析消息
            analysis_messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的数据分析助手。请基于提供的函数调用结果，生成清晰、有用的自然语言回答。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # 获取流式响应
            if model_config.provider == "volcengine":
                async for chunk in self._get_openai_streaming_response(model_config, analysis_messages):
                    if chunk:
                        yield chunk
            elif model_config.provider == "anthropic":
                async for chunk in self._get_anthropic_streaming_response(model_config, analysis_messages):
                    if chunk:
                        yield chunk
            elif model_config.provider == "ollama":
                async for chunk in self._get_ollama_streaming_response(model_config, analysis_messages):
                    if chunk:
                        yield chunk
        
        except Exception as e:
            yield f"⚠️ AI 分析过程中出现错误: {str(e)}\n"
    
    async def _format_mcp_result(self, result: dict, function_name: str) -> str:
        """格式化 MCP 调用结果，提供更友好的展示"""
        import json
        
        formatted_output = ""
        
        try:
            # 对于企业查询类结果的特殊处理
            if function_name in ['search_companies', 'search_established_companies', 'search_selfemployed', 'search_established_selfemployed']:
                if isinstance(result, dict) and 'data' in result:
                    data = result['data']
                    if 'num_found' in data:
                        formatted_output += f"📊 **查询统计**: 共找到 **{data['num_found']:,}** 条记录\n\n"
                    
                    if 'data_list' in data and isinstance(data['data_list'], list):
                        formatted_output += f"📋 **企业列表** (显示前 {min(len(data['data_list']), 10)} 条):\n\n"
                        for i, company in enumerate(data['data_list'][:10], 1):
                            formatted_output += f"**{i}. {company.get('companyName', '未知企业')}**\n"
                            if 'establishDate' in company:
                                formatted_output += f"   📅 成立时间: `{company['establishDate']}`\n"
                            if 'legalPerson' in company:
                                formatted_output += f"   👤 法定代表人: `{company['legalPerson']}`\n"
                            if 'capital' in company:
                                formatted_output += f"   💰 注册资本: `{company['capital']}`\n"
                            if 'companyStatusStr' in company:
                                formatted_output += f"   📈 企业状态: `{company['companyStatusStr']}`\n"
                            if 'creditNo' in company:
                                formatted_output += f"   🆔 统一信用代码: `{company['creditNo']}`\n"
                            formatted_output += "\n"
                        
                        if len(data['data_list']) > 10:
                            formatted_output += f"*... 还有 {len(data['data_list']) - 10:,} 条记录*\n\n"
                
                # 显示分页信息
                if isinstance(result, dict) and 'data' in result:
                    data = result['data']
                    if 'current_page' in data and 'total_page' in data:
                        formatted_output += f"📄 **分页信息**: 第 {data['current_page']} 页，共 {data['total_page']:,} 页\n\n"
            
            # 对于企业基本信息查询的特殊处理
            elif function_name == 'get_company_info':
                if isinstance(result, dict):
                    formatted_output += f"🏢 **企业基本信息**:\n\n"
                    info_fields = {
                        'CompanyName': ('🏢', '企业名称'),
                        'LegalPerson': ('👤', '法定代表人'),
                        'EstablishDate': ('📅', '成立时间'),
                        'Capital': ('💰', '注册资本'),
                        'CompanyType': ('🏷️', '企业类型'),
                        'CompanyStatus': ('📈', '企业状态'),
                        'CompanyAddress': ('🏠', '企业地址'),
                        'BusinessScope': ('💼', '经营范围'),
                        'CreditNo': ('🆔', '统一信用代码')
                    }
                    
                    for field, (emoji, label) in info_fields.items():
                        if field in result and result[field]:
                            value = result[field]
                            if field == 'BusinessScope' and len(value) > 200:
                                value = value[:200] + "..."
                            formatted_output += f"{emoji} **{label}**: `{value}`\n"
                    formatted_output += "\n"
            
            # 对于风险查询的特殊处理
            elif function_name == 'search_company_risk':
                if isinstance(result, dict):
                    formatted_output += f"⚠️ **企业风险信息**:\n\n"
                    risk_types = {
                        'self_risk': ('🔴', '自我风险'),
                        'relation_risk': ('🟡', '关联风险'),
                        'self_notice': ('ℹ️', '自身重要信息'),
                        'relation_notice': ('📢', '关联重要信息')
                    }
                    
                    for risk_type, (emoji, label) in risk_types.items():
                        if risk_type in result and result[risk_type].get('total', 0) > 0:
                            risk_data = result[risk_type]
                            formatted_output += f"{emoji} **{label}**: `{risk_data['total']}` 条记录\n"
                    formatted_output += "\n"
            
            # 对于科创评分的特殊处理
            elif function_name == 'get_stie_score':
                if isinstance(result, dict):
                    formatted_output += f"🧬 **企业科创能力评估**:\n\n"
                    if 'company_name' in result:
                        formatted_output += f"🏢 **企业名称**: `{result['company_name']}`\n"
                    if 'score' in result:
                        formatted_output += f"📊 **科创评分**: `{result['score']}`\n"
                    if 'level' in result:
                        formatted_output += f"🏆 **科创等级**: `{result['level']}`\n"
                    formatted_output += "\n"
            
            # 对于通用查询结果的处理
            else:
                if isinstance(result, dict):
                    # 显示状态信息
                    if 'statusCode' in result:
                        status_emoji = "✅" if result['statusCode'] == 1 else "❌"
                        status_text = "成功" if result['statusCode'] == 1 else "失败"
                        formatted_output += f"{status_emoji} **查询状态**: `{status_text}`\n"
                    
                    if 'statusMessage' in result:
                        formatted_output += f"📝 **状态信息**: `{result['statusMessage']}`\n\n"
            
            # 总是在最后显示美观的完整 JSON 数据
            formatted_output += f"🔍 **完整数据**:\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n\n"
            
        except Exception as e:
            # 如果格式化失败，回退到原始 JSON 显示
            formatted_output = f"⚠️ **数据格式化失败**: `{str(e)}`\n\n"
            formatted_output += f"📄 **原始数据**:\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n\n"
        
        return formatted_output
    
    async def _call_mcp_function(self, function_name: str, parameters: dict, selected_mcp: List[str], mcp_service) -> dict:
        """在选中的MCP中查找并执行函数"""
        for mcp_value in selected_mcp:
            try:
                # 获取该MCP的工具列表
                tools = await mcp_service.get_mcp_tools(mcp_value)
                
                # 检查函数是否存在于该MCP中
                function_exists = any(tool.get("name") == function_name for tool in tools)
                
                if function_exists:
                    # 执行MCP函数调用
                    result = await mcp_service.execute_mcp_function(mcp_value, function_name, parameters)
                    return result
            
            except Exception as e:
                print(f"MCP {mcp_value} 执行函数 {function_name} 失败: {e}")
                continue
        
        return None
    
    async def _enhance_messages_with_mcp(self, messages: List[Dict], selected_mcp: List[str] = None) -> List[Dict]:
        """使用MCP增强消息"""
        if not selected_mcp:
            return messages
        
        # 确保 messages 是字典列表格式
        enhanced_messages = []
        for msg in messages:
            if hasattr(msg, 'model_dump'):  # Pydantic 对象
                enhanced_messages.append(msg.model_dump())
            elif hasattr(msg, 'dict'):  # 旧版 Pydantic
                enhanced_messages.append(msg.dict())
            else:  # 已经是字典
                enhanced_messages.append(msg)
        
        # 构建详细的MCP工具上下文
        mcp_context = """你现在可以使用以下MCP工具来帮助用户。当需要调用工具时，请使用以下格式：

<|FunctionCallBegin|>
[{"name": "工具名称", "parameters": {"参数名": "参数值"}}]
<|FunctionCallEnd|>

可用的MCP工具：

"""
        
        for mcp_value in selected_mcp:
            mcp_config = self.config.get_mcp_config(mcp_value)
            if mcp_config:
                mcp_context += f"## {mcp_config.label} ({mcp_value})\n"
                mcp_context += f"描述: {mcp_config.description}\n\n"
                
                # 获取详细的工具列表
                try:
                    tools = await asyncio.wait_for(
                        self._get_mcp_tools_safe(mcp_config), 
                        timeout=5.0  # 增加超时时间到5秒
                    )
                    if tools:
                        for tool in tools:
                            tool_name = tool.get('name', 'unknown')
                            tool_desc = tool.get('description', '无描述')
                            tool_params = tool.get('parameters', {})
                            
                            mcp_context += f"### {tool_name}\n"
                            mcp_context += f"功能: {tool_desc}\n"
                            
                            # 添加参数信息
                            if tool_params and isinstance(tool_params, dict):
                                properties = tool_params.get('properties', {})
                                required = tool_params.get('required', [])
                                if properties:
                                    mcp_context += "参数:\n"
                                    for param_name, param_info in properties.items():
                                        param_type = param_info.get('type', 'string')
                                        param_desc = param_info.get('description', param_info.get('title', ''))
                                        is_required = param_name in required
                                        required_mark = " (必需)" if is_required else " (可选)"
                                        mcp_context += f"  - {param_name} ({param_type}){required_mark}: {param_desc}\n"
                            
                            # 添加调用示例
                            mcp_context += f"调用示例: <|FunctionCallBegin|>[{{\"name\": \"{tool_name}\", \"parameters\": {{}}}}]<|FunctionCallEnd|>\n\n"
                    else:
                        mcp_context += "工具加载中，请稍后...\n\n"
                except asyncio.TimeoutError:
                    mcp_context += "工具加载超时，请稍后重试\n\n"
                except Exception as e:
                    mcp_context += f"工具加载失败: {str(e)}\n\n"
        
        mcp_context += """
重要提示：
1. 当用户询问需要查询数据时，请根据用户的具体需求选择合适的工具
2. 调用工具前，请确保参数正确且完整
3. 必需参数不能为空，可选参数可以省略或设为null
4. 每次只调用一个工具，等待结果后再决定是否需要调用其他工具
5. 调用工具后，请根据返回的结果向用户提供有用的信息
"""
        
        # 如果第一条消息是系统消息，则追加MCP上下文
        if enhanced_messages and enhanced_messages[0].get("role") == "system":
            enhanced_messages[0]["content"] += f"\n\n{mcp_context}"
        else:
            # 否则在开头插入系统消息
            enhanced_messages.insert(0, {
                "role": "system",
                "content": mcp_context
            })
        
        return enhanced_messages
    
    async def _get_openai_response(self, model_config: AIModelConfig, messages: List[Dict]) -> str:
        """获取OpenAI响应"""
        client = self._get_client(model_config)
        
        try:
            response = await client.chat.completions.create(
                model=model_config.model_id,
                messages=messages,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API 调用失败: {str(e)}")
    
    async def _get_openai_streaming_response(self, model_config: AIModelConfig, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """获取OpenAI流式响应"""
        client = self._get_client(model_config)
        
        try:
            stream = await client.chat.completions.create(
                model=model_config.model_id,
                messages=messages,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"OpenAI Streaming API 调用失败: {str(e)}")
    
    async def _get_anthropic_response(self, model_config: AIModelConfig, messages: List[Dict]) -> str:
        """获取Anthropic响应"""
        client = self._get_client(model_config)
        
        try:
            # 转换消息格式（Anthropic要求不同的格式）
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            response = await client.messages.create(
                model=model_config.model_id,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
                system=system_message,
                messages=user_messages
            )
            
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic API 调用失败: {str(e)}")
    
    async def _get_anthropic_streaming_response(self, model_config: AIModelConfig, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """获取Anthropic流式响应"""
        client = self._get_client(model_config)
        
        try:
            # 转换消息格式
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            async with client.messages.stream(
                model=model_config.model_id,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
                system=system_message,
                messages=user_messages
            ) as stream:
                async for chunk in stream.text_stream:
                    yield chunk
        except Exception as e:
            raise Exception(f"Anthropic Streaming API 调用失败: {str(e)}")
    
    async def _get_ollama_response(self, model_config: AIModelConfig, messages: List[Dict]) -> str:
        """获取Ollama响应"""
        client = self._get_client(model_config)
        
        try:
            response = await client.post("/api/chat", json={
                "model": model_config.model_id,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": model_config.temperature,
                    "num_predict": model_config.max_tokens
                }
            })
            response.raise_for_status()
            return response.json()["message"]["content"]
        except Exception as e:
            raise Exception(f"Ollama API 调用失败: {str(e)}")
    
    async def _get_ollama_streaming_response(self, model_config: AIModelConfig, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """获取Ollama流式响应"""
        client = self._get_client(model_config)
        
        try:
            async with client.stream("POST", "/api/chat", json={
                "model": model_config.model_id,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": model_config.temperature,
                    "num_predict": model_config.max_tokens
                }
            }) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
        except Exception as e:
            raise Exception(f"Ollama Streaming API 调用失败: {str(e)}")
    
    async def _get_mcp_tools_safe(self, mcp_config):
        """安全获取 MCP 工具列表，不阻塞主流程"""
        try:
            from mcp_service import MCPService
            mcp_service = MCPService(self.config)
            return await mcp_service.get_mcp_tools(mcp_config.value)
        except Exception:
            return []
    
    def is_healthy(self) -> bool:
        """检查服务健康状态"""
        try:
            # 检查是否有可用的模型配置
            available_models = self.config.get_available_models()
            return len([m for m in available_models if m["available"]]) > 0
        except Exception:
            return False 