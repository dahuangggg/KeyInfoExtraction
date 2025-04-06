from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Index, UniqueConstraint, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base_class import Base

class KnowledgeBase(Base):
    """知识库模型，用于存储标准库和提取数据的物理状态信息"""
    
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    physical_group_name = Column(String(255), nullable=False, index=True)  # 物理状态组名称
    physical_state_name = Column(String(255), nullable=False, index=True)  # 物理状态名称
    test_item_name = Column(String(255), nullable=True, index=True)  # 试验项目名称
    physical_state_value = Column(Text, nullable=True)  # 物理状态值
    risk_assessment = Column(String(50), nullable=True)  # 风险评价（可用/限用/禁用）
    detailed_analysis = Column(Text, nullable=True)  # 详细分析/测试评语
    
    # 数据来源信息
    source = Column(String(20), nullable=False, index=True)  # 'standard'或'extraction'
    reference_id = Column(Integer, nullable=True, index=True)  # 关联到extraction_result_id
    
    # 元数据
    import_time = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 添加联合索引，提高查询性能
    __table_args__ = (
        Index('idx_knowledge_base_lookup', 
              'physical_group_name', 'physical_state_name', 'test_item_name', 'source'),
    )
    
    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, group={self.physical_group_name}, state={self.physical_state_name})>" 