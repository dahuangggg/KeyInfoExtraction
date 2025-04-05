from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class KnowledgeBaseBase(BaseModel):
    """知识库条目基础模式"""
    category: str
    key: str
    source_document_id: Optional[int] = None


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识库条目模式"""
    value: Dict[str, Any]


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库条目模式"""
    category: Optional[str] = None
    key: Optional[str] = None
    value: Optional[Dict[str, Any]] = None
    source_document_id: Optional[int] = None


class KnowledgeBaseResponse(KnowledgeBaseBase):
    """知识库条目响应模式"""
    id: int
    value: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeBaseImport(BaseModel):
    """从提取结果导入知识库模式"""
    document_id: int 