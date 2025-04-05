from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_extraction_service
from app.services.knowledge_service import KnowledgeBaseService
from app.services.extraction_service import InformationExtractionService
from app.schemas.knowledge import (
    KnowledgeBaseResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseImport
)

router = APIRouter()


@router.post("/", response_model=KnowledgeBaseResponse, deprecated=True)
def create_knowledge_item(
    item: KnowledgeBaseCreate,
    db: Session = Depends(get_db_session)
):
    """
    创建新的知识库条目（已弃用）
    
    本API已弃用，知识库现在主要用于辅助提取任务，请使用 POST /api/v1/knowledge/documents/{document_id} 从文档创建知识库条目
    """
    knowledge_service = KnowledgeBaseService(db)
    try:
        knowledge_item = knowledge_service.create_knowledge_item(
            category=item.category,
            key=item.key,
            value=item.value,
            source_document_id=item.source_document_id
        )
        return knowledge_item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建知识库条目时出错: {str(e)}")


@router.get("/", response_model=List[KnowledgeBaseResponse], deprecated=True)
def search_knowledge(
    query: str = None,
    category: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """
    搜索知识库条目（已弃用）
    
    本API已弃用，知识库现在主要用于辅助提取任务
    """
    knowledge_service = KnowledgeBaseService(db)
    items = knowledge_service.search_knowledge(
        query=query,
        category=category,
        skip=skip,
        limit=limit
    )
    return items


@router.get("/categories", response_model=List[str], deprecated=True)
def get_categories(
    db: Session = Depends(get_db_session)
):
    """
    获取所有知识类别（已弃用）
    
    本API已弃用，知识库现在主要用于辅助提取任务
    """
    knowledge_service = KnowledgeBaseService(db)
    categories = knowledge_service.get_categories()
    return categories


@router.get("/{item_id}", response_model=KnowledgeBaseResponse, deprecated=True)
def get_knowledge_item(
    item_id: int,
    db: Session = Depends(get_db_session)
):
    """
    获取单个知识库条目（已弃用）
    
    本API已弃用，知识库现在主要用于辅助提取任务
    """
    knowledge_service = KnowledgeBaseService(db)
    item = knowledge_service.get_knowledge_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"知识条目ID {item_id} 不存在")
    return item


@router.put("/{item_id}", response_model=KnowledgeBaseResponse, deprecated=True)
def update_knowledge_item(
    item_id: int,
    item: KnowledgeBaseUpdate,
    db: Session = Depends(get_db_session)
):
    """
    更新知识库条目（已弃用）
    
    本API已弃用，知识库现在主要用于辅助提取任务
    """
    knowledge_service = KnowledgeBaseService(db)
    try:
        updated_item = knowledge_service.update_knowledge_item(
            item_id=item_id,
            data=item.dict(exclude_unset=True)
        )
        return updated_item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新知识库条目时出错: {str(e)}")


@router.delete("/{item_id}", deprecated=True)
def delete_knowledge_item(
    item_id: int,
    db: Session = Depends(get_db_session)
):
    """
    删除知识库条目（已弃用）
    
    本API已弃用，知识库现在主要用于辅助提取任务
    """
    knowledge_service = KnowledgeBaseService(db)
    try:
        result = knowledge_service.delete_knowledge_item(item_id)
        return {"success": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除知识库条目时出错: {str(e)}")


@router.post("/documents/{document_id}", response_model=Dict[str, Any])
def create_knowledge_from_document(
    document_id: int,
    db: Session = Depends(get_db_session),
    extraction_service: InformationExtractionService = Depends(get_extraction_service)
):
    """
    从文档提取结果创建知识库条目
    
    这是唯一保留的知识库API，用于辅助提取任务
    
    参数:
        document_id: 文档ID，从该文档的提取结果中创建知识库条目
    """
    knowledge_service = KnowledgeBaseService(db)
    
    try:
        # 获取提取结果
        extraction_data = extraction_service.get_extraction_result(document_id)
        if not extraction_data:
            raise HTTPException(status_code=404, detail=f"文档ID {document_id} 的提取结果不存在")
        
        # 校验提取结果数据
        if not isinstance(extraction_data, dict) or "元器件物理状态分析" not in extraction_data:
            raise HTTPException(status_code=400, detail="提取结果数据格式不正确，缺少元器件物理状态分析")
        
        physical_state_analysis = extraction_data.get("元器件物理状态分析", [])
        if not isinstance(physical_state_analysis, list) or len(physical_state_analysis) == 0:
            raise HTTPException(status_code=400, detail="提取结果的元器件物理状态分析数据为空或格式不正确")
        
        # 导入到知识库
        imported_items = knowledge_service.import_from_extraction(
            document_id=document_id,
            extraction_data=extraction_data
        )
        
        return {
            "success": True,
            "imported_count": len(imported_items)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"从文档创建知识库条目时出错: {str(e)}")


# 保留原有的import路由以维持向后兼容性，但标记为弃用
@router.post("/import", response_model=Dict[str, Any], deprecated=True)
def import_from_extraction(
    import_data: KnowledgeBaseImport,
    db: Session = Depends(get_db_session),
    extraction_service: InformationExtractionService = Depends(get_extraction_service)
):
    """
    从提取结果导入到知识库 (已弃用，请使用 POST /api/v1/knowledge/documents/{document_id})
    """
    knowledge_service = KnowledgeBaseService(db)
    
    try:
        # 获取提取结果
        extraction_data = extraction_service.get_extraction_result(import_data.document_id)
        if not extraction_data:
            raise HTTPException(status_code=404, detail=f"文档ID {import_data.document_id} 的提取结果不存在")
        
        # 导入到知识库
        imported_items = knowledge_service.import_from_extraction(
            document_id=import_data.document_id,
            extraction_data=extraction_data
        )
        
        return {
            "success": True,
            "imported_count": len(imported_items)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入知识库时出错: {str(e)}") 