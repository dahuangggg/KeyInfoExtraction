from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_extraction_service
from app.services.edit_history_service import EditHistoryService
from app.services.extraction_service import InformationExtractionService
from app.models.edit_history import EditHistory

router = APIRouter()


@router.get("/{document_id}", response_model=List[dict])
def get_document_edit_history(
    document_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """
    获取文档的编辑历史
    """
    edit_service = EditHistoryService(db)
    try:
        history = edit_service.get_document_edit_history(
            document_id=document_id,
            skip=skip,
            limit=limit
        )
        
        # 转换为字典列表，以便更好地序列化
        result = []
        for item in history:
            result.append({
                "id": item.id,
                "document_id": item.document_id,
                "edit_time": item.edit_time,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "field_name": item.field_name,
                "old_value": item.old_value,
                "new_value": item.new_value
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取编辑历史时出错: {str(e)}")

@router.post("/{document_id}/revert/{history_id}", response_model=Dict[str, Any])
def revert_to_history_point(
    document_id: int,
    history_id: int,
    db: Session = Depends(get_db_session),
    extraction_service: InformationExtractionService = Depends(get_extraction_service)
):
    """
    回溯到特定历史点的文档状态
    
    这个端点将文档回溯到指定的历史记录点的状态。它会撤销所有在指定历史点之后的编辑操作。
    
    参数:
        document_id: 文档ID
        history_id: 要回溯到的历史记录ID
    
    返回:
        回溯后的提取结果
    """
    edit_service = EditHistoryService(db)
    try:
        # 执行回溯操作
        reverted_result = edit_service.revert_to_history_point(
            document_id=document_id,
            history_id=history_id,
            extraction_service=extraction_service
        )
        
        return reverted_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回溯到历史点时出错: {str(e)}") 