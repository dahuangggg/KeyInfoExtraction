from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models.document import Document
from app.services.document_service import DocumentService
from app.schemas.document import DocumentResponse, DocumentListResponse, BatchUploadResponse

router = APIRouter()


@router.post("/", response_model=BatchUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db_session)
):
    """
    上传一个或多个文档
    
    支持批量上传多个文件，每个文件都会单独处理并保存到数据库中。
    即使只上传一个文件，也会返回批量上传的响应格式。
    """
    document_service = DocumentService(db)
    documents = await document_service.upload_documents(files)
    
    # 返回上传成功的文档数量和文档列表
    return {
        "total": len(files),
        "successful": len(documents),
        "documents": documents
    }


@router.get("/", response_model=List[DocumentListResponse])
def get_all_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db_session)
):
    """
    获取所有文档列表，支持分页
    """
    document_service = DocumentService(db)
    documents = document_service.get_all_documents(skip, limit)
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
    删除文档及其所有关联数据
    """
    document_service = DocumentService(db)
    success = document_service.delete_document(document_id)
    return {"success": success} 