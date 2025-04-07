from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.db.session import get_db
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import (
    KnowledgeBaseResponse
)
from app.services.knowledge_service import KnowledgeBaseService
from app.api.deps import get_extraction_service
from app.services.extraction_service import InformationExtractionService

router = APIRouter()

@router.post("/{document_id}", response_model=Dict[str, Any])
def create_knowledge_from_document(
    document_id: int,
    db: Session = Depends(get_db),
    extraction_service: InformationExtractionService = Depends(get_extraction_service)
):
    """
    基于文档ID创建知识库条目
    
    此接口将根据指定文档ID的提取结果，将文档中的物理状态分析数据导入到知识库中。
    文档必须已经过提取处理并且包含物理状态分析数据。
    
    参数:
        document_id: 要导入到知识库的文档ID
        
    返回:
        导入结果，包含成功导入的条目数量
    """
    knowledge_service = KnowledgeBaseService(db)
    
    try:
        # 获取提取结果
        extraction_result = extraction_service.get_extraction_result(document_id)
        if not extraction_result:
            raise HTTPException(status_code=404, detail=f"文档ID {document_id} 的提取结果不存在")
        
        # 校验提取结果数据
        if not isinstance(extraction_result, dict) or "元器件物理状态分析" not in extraction_result:
            raise HTTPException(status_code=400, detail="提取结果数据格式不正确，缺少元器件物理状态分析")
        
        physical_state_analysis = extraction_result.get("元器件物理状态分析", [])
        if not isinstance(physical_state_analysis, list) or len(physical_state_analysis) == 0:
            raise HTTPException(status_code=400, detail="提取结果的元器件物理状态分析数据为空或格式不正确")
        
        # 导入到知识库
        imported_items = knowledge_service.import_from_extraction(
            extraction_result_id=document_id,
            extraction_data=extraction_result
        )
        
        return {
            "success": True,
            "imported_count": len(imported_items)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"从文档创建知识库条目时出错: {str(e)}") 