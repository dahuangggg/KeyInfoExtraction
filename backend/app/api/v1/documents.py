from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models.document import Document
from app.services.document_service import DocumentService
from app.schemas.document import DocumentResponse, DocumentListResponse

router = APIRouter()


@router.post("/", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session)
):
    """
    上传新文档
    """
    document_service = DocumentService(db)
    document = await document_service.upload_document(file)
    return document


@router.get("/", response_model=List[DocumentListResponse])
def get_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """
    获取所有文档列表
    """
    document_service = DocumentService(db)
    documents = document_service.get_all_documents(skip=skip, limit=limit)
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db_session)
):
    """
    获取单个文档详情
    """
    document_service = DocumentService(db)
    document = document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档未找到")
    return document


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db_session)
):
    """
    删除文档及其关联数据
    """
    document_service = DocumentService(db)
    result = document_service.delete_document(document_id)
    return {"success": result} 