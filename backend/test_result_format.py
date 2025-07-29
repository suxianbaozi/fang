#!/usr/bin/env python3

import asyncio
import json
from ai_service import AIService
from config import Config

async def test_beautiful_formatting():
    """测试美观的结果格式化"""
    config = Config()
    ai_service = AIService(config)
    
    # 测试企业查询结果格式化
    mock_search_result = {
        "data": {
            "data_list": [
                {
                    "companyName": "凭安征信有限公司",
                    "creditNo": "91310000123456789X",
                    "establishDate": "2020-01-01",
                    "legalPerson": "张三",
                    "capital": "1000万人民币",
                    "companyStatusStr": "在业"
                },
                {
                    "companyName": "四币同铸企业发展（上海）有限公司",
                    "creditNo": "91310114MA1GWLBF8W",
                    "establishDate": "2019-11-02",
                    "legalPerson": "朱莉",
                    "capital": "769200000万人民币",
                    "companyStatusStr": "在业"
                }
            ],
            "total_page": 1500,
            "current_page": 1,
            "num_found": 2919139
        },
        "statusCode": 1,
        "statusMessage": "请求成功"
    }
    
    print("🎨 测试美观的企业查询结果格式化...")
    print("="*80)
    formatted = await ai_service._format_mcp_result(mock_search_result, "search_companies")
    print(formatted)
    
    # 测试企业基本信息格式化
    mock_info_result = {
        "CompanyName": "凭安征信有限公司",
        "LegalPerson": "张三",
        "EstablishDate": "2020-01-01",
        "Capital": "1000万人民币",
        "CompanyType": "有限责任公司",
        "CompanyStatus": "在业",
        "CompanyAddress": "上海市浦东新区张江高科技园区科苑路399号张江创新园10号楼",
        "BusinessScope": "征信业务;信用评估;数据处理和存储服务;软件开发;信息技术咨询服务;企业信用调查和评估;信用管理咨询服务",
        "CreditNo": "91310000123456789X"
    }
    
    print("\n" + "="*80)
    print("🏢 测试企业信息格式化...")
    print("="*80)
    formatted = await ai_service._format_mcp_result(mock_info_result, "get_company_info")
    print(formatted)
    
    # 测试科创评分格式化
    mock_score_result = {
        "company_name": "凭安征信有限公司",
        "score": 85.6,
        "level": "A级",
        "ranking": {
            "industry_ranking": 15.2
        }
    }
    
    print("\n" + "="*80)
    print("🧬 测试科创评分格式化...")
    print("="*80)
    formatted = await ai_service._format_mcp_result(mock_score_result, "get_stie_score")
    print(formatted)

async def test_parameters_formatting():
    """测试参数格式化显示"""
    print("📋 参数格式化示例:")
    print("="*50)
    
    # 模拟复杂参数
    parameters = {
        "company_names": ["凭安征信有限公司", "上海征信公司"],
        "province": "上海",
        "city": "上海市",
        "company_status": "正常",
        "establish_date": "2020-01-01@2024-12-31",
        "page_size": 10
    }
    
    print("📋 **参数**:")
    print(f"```json\n{json.dumps(parameters, ensure_ascii=False, indent=2)}\n```")

if __name__ == "__main__":
    print("🎨 测试美观的 MCP 结果格式化...")
    print()
    
    asyncio.run(test_beautiful_formatting())
    print("\n" + "="*80 + "\n")
    asyncio.run(test_parameters_formatting()) 