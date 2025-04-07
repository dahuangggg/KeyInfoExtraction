from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class DocumentBase(BaseModel):
    """文档基础模式"""
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    processed: bool


class DocumentCreate(DocumentBase):
    """创建文档模式"""
    file_path: str
    upload_time: datetime


class DocumentResponse(DocumentBase):
    """文档响应模式"""
    id: int
    file_path: str
    upload_time: datetime
    processing_time: Optional[float] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应模式"""
    id: int
    original_filename: str
    file_type: str
    file_size: int
    upload_time: datetime
    processed: bool
    processing_time: Optional[float] = None

    class Config:
        from_attributes = True


class BatchUploadResponse(BaseModel):
    """批量上传响应模式"""
    total: int  # 上传的总文件数
    successful: int  # 成功上传的文件数
    documents: List[DocumentResponse]  # 成功上传的文档列表

    class Config:
        from_attributes = True


class BatchDeleteRequest(BaseModel):
    """批量删除请求模式"""
    document_ids: List[int]  # 要删除的文档ID列表 