from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class KnowledgeBaseBase(BaseModel):
    """知识库条目的基本模型"""
    
    physical_group_name: str = Field(..., description="物理状态组名称")
    physical_state_name: str = Field(..., description="物理状态名称")
    test_item_name: Optional[str] = Field(None, description="试验项目名称")
    physical_state_value: Optional[str] = Field(None, description="物理状态值")
    risk_assessment: Optional[str] = Field(None, description="风险评价")
    detailed_analysis: Optional[str] = Field(None, description="详细分析")
    source: str = Field(..., description="数据来源", example="standard")
    reference_id: Optional[int] = Field(None, description="引用ID")

class KnowledgeBaseResponse(KnowledgeBaseBase):
    """知识库条目的响应模型"""
    
    id: int
    import_time: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True 