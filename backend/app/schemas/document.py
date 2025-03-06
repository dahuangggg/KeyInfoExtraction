from datetime import datetime
from typing import Optional, List
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
        orm_mode = True


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
        orm_mode = True 