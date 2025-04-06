from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base_class import Base

class Document(Base):
    """文档模型，用于存储上传的文档信息"""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # 文件大小（字节）
    file_type = Column(String(50), nullable=False)  # 文件类型（doc/docx）
    upload_time = Column(DateTime, default=datetime.now)
    processed = Column(Boolean, default=False)  # 是否已处理
    processing_time = Column(Float, nullable=True)  # 处理时间（秒）
    
    # 关联提取结果
    extraction_results = relationship("ExtractionResult", back_populates="document", cascade="all, delete-orphan")
    
    # 关联修改历史
    edit_histories = relationship("EditHistory", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename})>" 