from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base_class import Base

class ExtractionResult(Base):
    """提取结果模型，用于存储文档提取的结果"""
    
    __tablename__ = "extraction_results"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    extraction_time = Column(DateTime, default=datetime.now)
    result_json = Column(JSON, nullable=False)  # 存储提取结果的JSON
    is_edited = Column(Boolean, default=False)  # 是否经过编辑
    last_edit_time = Column(DateTime, nullable=True)  # 最后编辑时间
    
    # 关联文档
    document = relationship("Document", back_populates="extraction_results")
    
    # 关联物理状态组
    physical_state_groups = relationship("PhysicalStateGroup", back_populates="extraction_result", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ExtractionResult(id={self.id}, document_id={self.document_id})>"

class PhysicalStateGroup(Base):
    """物理状态组模型"""
    
    __tablename__ = "physical_state_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    extraction_result_id = Column(Integer, ForeignKey("extraction_results.id"), nullable=False)
    group_name = Column(String(255), nullable=False)  # 物理状态组名称
    
    # 关联提取结果
    extraction_result = relationship("ExtractionResult", back_populates="physical_state_groups")
    
    # 关联物理状态项
    physical_state_items = relationship("PhysicalStateItem", back_populates="physical_state_group", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PhysicalStateGroup(id={self.id}, group_name={self.group_name})>"

class PhysicalStateItem(Base):
    """物理状态项模型"""
    
    __tablename__ = "physical_state_items"
    
    id = Column(Integer, primary_key=True, index=True)
    physical_state_group_id = Column(Integer, ForeignKey("physical_state_groups.id"), nullable=False)
    state_name = Column(String(255), nullable=False)  # 物理状态名称
    state_value = Column(Text, nullable=True)  # 典型物理状态值
    prohibition_info = Column(Text, nullable=True)  # 禁限用信息
    test_comment = Column(Text, nullable=True)  # 测试评语
    test_project = Column(Text, nullable=True)  # 试验项目
    
    # 关联物理状态组
    physical_state_group = relationship("PhysicalStateGroup", back_populates="physical_state_items")
    
    def __repr__(self):
        return f"<PhysicalStateItem(id={self.id}, state_name={self.state_name})>" 