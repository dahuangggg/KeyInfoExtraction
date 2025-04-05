from typing import Generator
import os
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.db import get_db
from app.services.extraction_service import InformationExtractionService
from app.extractors.llm_extractor import LLMExtractor
from app.core.config import settings

# 创建LLMExtractor全局单例
_LLM_EXTRACTOR = None

def get_llm_extractor():
    """
    获取LLM提取器单例
    """
    global _LLM_EXTRACTOR
    if _LLM_EXTRACTOR is None:
        # 获取backend目录的绝对路径
        current_file = os.path.abspath(__file__)  # 当前文件的绝对路径
        app_dir = os.path.dirname(os.path.dirname(current_file))  # app目录
        backend_dir = os.path.dirname(app_dir)  # backend目录
        
        # 解析配置文件路径 - 支持相对路径和绝对路径
        format_json_path = settings.FORMAT_JSON_PATH
        terminology_file_path = settings.TERMINOLOGY_FILE_PATH
        
        # 如果是相对路径，则相对于backend目录解析
        if not os.path.isabs(format_json_path):
            format_json_path = os.path.join(backend_dir, format_json_path)
        if not os.path.isabs(terminology_file_path):
            terminology_file_path = os.path.join(backend_dir, terminology_file_path)
        
        # 检查文件是否存在
        if not os.path.exists(format_json_path):
            raise FileNotFoundError(f"格式定义文件不存在: {format_json_path}")
        if not os.path.exists(terminology_file_path):
            raise FileNotFoundError(f"术语文件不存在: {terminology_file_path}")
            
        # 详细打印文件路径和文件大小，帮助调试
        format_file_size = os.path.getsize(format_json_path)
        term_file_size = os.path.getsize(terminology_file_path)
        
        print(f"格式文件路径: {format_json_path} (大小: {format_file_size} 字节)")
        print(f"术语文件路径: {terminology_file_path} (大小: {term_file_size} 字节)")
        print(f"LLM模式: {settings.LLM_MODE}")
        
        # 确保这些文件可以被正常读取
        try:
            with open(format_json_path, 'r', encoding='utf-8') as f:
                format_data = json.load(f)
                print(f"格式文件加载成功，包含 {len(format_data)} 个条目")
            
            with open(terminology_file_path, 'r', encoding='utf-8') as f:
                term_count = sum(1 for line in f if line.strip())
                print(f"术语文件加载成功，包含约 {term_count} 个术语")
        except Exception as e:
            print(f"文件读取测试失败: {str(e)}")
            raise
        
        # 根据配置的模式决定使用API密钥还是本地服务器
        if settings.LLM_MODE.lower() == "api":
            print(f"使用API模式，模型: {settings.LLM_MODEL}")
            # 创建LLM提取器实例 - API模式
            _LLM_EXTRACTOR = LLMExtractor(
                format_json_path=format_json_path,
                terminology_file=terminology_file_path,
                model_name=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                debug=settings.DEBUG,
                use_api=True  # 显式指定使用API模式
            )
        else:
            print(f"使用本地服务器模式，服务器: {settings.LLM_SERVER_IP}:{settings.LLM_SERVER_PORT}")
            # 创建LLM提取器实例 - 本地服务器模式
            _LLM_EXTRACTOR = LLMExtractor(
                format_json_path=format_json_path,
                terminology_file=terminology_file_path,
                server_ip=settings.LLM_SERVER_IP,
                server_port=int(settings.LLM_SERVER_PORT),
                model_name=settings.LLM_SERVER_MODEL,
                debug=settings.DEBUG,
                use_api=False  # 显式指定使用本地服务器模式
            )
    return _LLM_EXTRACTOR

# 直接使用原始的get_db函数作为依赖
get_db_session = get_db

def get_extraction_service(db: Session = Depends(get_db)) -> InformationExtractionService:
    """
    获取信息提取服务依赖
    
    返回配置了数据库连接和LLM提取器的InformationExtractionService实例
    """
    # 获取LLM提取器单例
    extractor = get_llm_extractor()
    
    # 创建并返回一个配置了数据库连接和LLM提取器的服务实例
    return InformationExtractionService(db=db, extractor=extractor) 