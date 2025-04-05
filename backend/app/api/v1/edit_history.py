from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.services.edit_history_service import EditHistoryService
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