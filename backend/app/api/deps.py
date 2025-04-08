from typing import Generator
import os
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.db import get_db
from app.services.extraction_service import InformationExtractionService
from app.extractors.llm_extractor import LLMExtractor
from app.extractors.llm_service import LLMService
from app.core.config import settings

# 创建LLMExtractor全局单例
_LLM_EXTRACTOR = None
# 创建LLMService全局单例
_LLM_SERVICE = None

def get_llm_service():
    """获取LLM服务实例"""
    global _LLM_SERVICE
    if _LLM_SERVICE is None:
        # 根据配置的模式决定使用API密钥还是本地服务器
        if settings.LLM_MODE.lower() == "api":
            # 创建LLM服务实例 - API模式
            _LLM_SERVICE = LLMService(
                model_name=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                debug=settings.DEBUG,
                use_api=True  # 显式指定使用API模式
            )
        else:
            # 创建LLM服务实例 - 本地服务器模式
            _LLM_SERVICE = LLMService(
                model_name=settings.LLM_SERVER_MODEL,
                server_ip=settings.LLM_SERVER_IP,
                server_port=int(settings.LLM_SERVER_PORT),
                debug=settings.DEBUG,
                use_api=False  # 显式指定使用本地服务器模式
            )
    return _LLM_SERVICE

def get_llm_extractor():
    """获取LLM提取器实例"""
    global _LLM_EXTRACTOR
    if _LLM_EXTRACTOR is None:
        # 获取LLM服务实例
        llm_service = get_llm_service()
        
        # 初始化LLM提取器
        _LLM_EXTRACTOR = LLMExtractor(
            llm_service=llm_service,
            debug=settings.DEBUG
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