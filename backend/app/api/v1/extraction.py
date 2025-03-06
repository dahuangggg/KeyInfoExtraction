from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_extraction_service
from app.services.extraction_service import InformationExtractionService
from app.services.edit_history_service import EditHistoryService
from app.schemas.extraction import ExtractionResultResponse, ExtractionResultEdit

router = APIRouter()


@router.post("/{document_id}/process", response_model=Dict[str, Any])
async def process_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    extraction_service: InformationExtractionService = Depends(get_extraction_service),
    db: Session = Depends(get_db_session)
):
    """
    处理文档并提取信息
    """
    try:
        # 在后台任务中处理文档
        background_tasks.add_task(extraction_service.process_document_by_id, document_id)
        return {"status": "processing", "document_id": document_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文档时出错: {str(e)}")


@router.get("/{document_id}/result", response_model=Dict[str, Any])
def get_extraction_result(
    document_id: int,
    extraction_service: InformationExtractionService = Depends(get_extraction_service),
    db: Session = Depends(get_db_session)
):
    """
    获取文档的提取结果
    """
    try:
        result = extraction_service.get_extraction_result(document_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"文档ID {document_id} 的提取结果不存在")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提取结果时出错: {str(e)}")


@router.put("/{document_id}/edit", response_model=Dict[str, Any])
def edit_extraction_result(
    document_id: int,
    edit_data: ExtractionResultEdit,
    db: Session = Depends(get_db_session)
):
    """
    编辑提取结果
    """
    try:
        edit_service = EditHistoryService(db)
        result = edit_service.edit_extraction_result(
            document_id=document_id,
            user_id=edit_data.user_id,
            user_name=edit_data.user_name,
            edit_data=edit_data.dict()
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"编辑提取结果时出错: {str(e)}")


@router.post("/{document_id}/process_text", response_model=Dict[str, Any])
def process_text(
    document_id: int,
    text: str,
    section_type: str = "通用",
    extraction_service: InformationExtractionService = Depends(get_extraction_service),
    db: Session = Depends(get_db_session)
):
    """
    处理文本并提取信息
    """
    try:
        result = extraction_service.process_text(text, section_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文本时出错: {str(e)}") 