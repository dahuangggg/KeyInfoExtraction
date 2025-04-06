from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base_class import Base

class EditHistory(Base):
    """编辑历史模型，用于记录用户对提取结果的修改"""
    
    __tablename__ = "edit_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    edit_time = Column(DateTime, default=datetime.now)
    
    # 修改内容
    entity_type = Column(String(50), nullable=False)  # 修改的实体类型（物理状态组/物理状态项）
    entity_id = Column(Integer, nullable=False)  # 修改的实体ID
    field_name = Column(String(50), nullable=False)  # 修改的字段名
    old_value = Column(Text, nullable=True)  # 修改前的值
    new_value = Column(Text, nullable=True)  # 修改后的值
    
    # 关联文档
    document = relationship("Document", back_populates="edit_histories")
    
    def __repr__(self):
        return f"<EditHistory(id={self.id}, document_id={self.document_id}, field_name={self.field_name})>" 