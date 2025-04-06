from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base_class import Base

class KnowledgeBase(Base):
    """知识库模型，用于存储提取和复核后的结构化数据"""
    
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)  # 知识类别
    key = Column(String(255), nullable=False, index=True)  # 知识键
    value = Column(JSON, nullable=False)  # 知识值（JSON格式）
    source_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # 来源文档ID
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, category={self.category}, key={self.key})>" 