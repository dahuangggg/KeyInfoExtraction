from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.services.knowledge_service import KnowledgeBaseService
from app.services.extraction_service import InformationExtractionService
from app.schemas.knowledge import (
    KnowledgeBaseResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseImport
)

router = APIRouter()


@router.post("/", response_model=KnowledgeBaseResponse)
def create_knowledge_item(
    item: KnowledgeBaseCreate,
    db: Session = Depends(get_db_session)
):
    """
    创建新的知识库条目
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


@router.get("/", response_model=List[KnowledgeBaseResponse])
def search_knowledge(
    query: str = None,
    category: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """
    搜索知识库条目
    """
    knowledge_service = KnowledgeBaseService(db)
    items = knowledge_service.search_knowledge(
        query=query,
        category=category,
        skip=skip,
        limit=limit
    )
    return items


@router.get("/categories", response_model=List[str])
def get_categories(
    db: Session = Depends(get_db_session)
):
    """
    获取所有知识类别
    """
    knowledge_service = KnowledgeBaseService(db)
    categories = knowledge_service.get_categories()
    return categories


@router.get("/{item_id}", response_model=KnowledgeBaseResponse)
def get_knowledge_item(
    item_id: int,
    db: Session = Depends(get_db_session)
):
    """
    获取单个知识库条目
    """
    knowledge_service = KnowledgeBaseService(db)
    item = knowledge_service.get_knowledge_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"知识条目ID {item_id} 不存在")
    return item


@router.put("/{item_id}", response_model=KnowledgeBaseResponse)
def update_knowledge_item(
    item_id: int,
    item: KnowledgeBaseUpdate,
    db: Session = Depends(get_db_session)
):
    """
    更新知识库条目
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


@router.delete("/{item_id}")
def delete_knowledge_item(
    item_id: int,
    db: Session = Depends(get_db_session)
):
    """
    删除知识库条目
    """
    knowledge_service = KnowledgeBaseService(db)
    try:
        result = knowledge_service.delete_knowledge_item(item_id)
        return {"success": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除知识库条目时出错: {str(e)}")


@router.post("/import", response_model=Dict[str, Any])
def import_from_extraction(
    import_data: KnowledgeBaseImport,
    db: Session = Depends(get_db_session)
):
    """
    从提取结果导入到知识库
    """
    knowledge_service = KnowledgeBaseService(db)
    extraction_service = InformationExtractionService(db)
    
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