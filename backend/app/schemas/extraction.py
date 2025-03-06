from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class PhysicalStateItemBase(BaseModel):
    """物理状态项基础模式"""
    state_name: str
    state_value: str
    prohibition_info: Optional[str] = None
    test_comment: Optional[str] = None


class PhysicalStateItemResponse(PhysicalStateItemBase):
    """物理状态项响应模式"""
    id: int
    physical_state_group_id: int

    class Config:
        orm_mode = True


class PhysicalStateGroupBase(BaseModel):
    """物理状态组基础模式"""
    group_name: str


class PhysicalStateGroupResponse(PhysicalStateGroupBase):
    """物理状态组响应模式"""
    id: int
    extraction_result_id: int
    items: List[PhysicalStateItemResponse] = []

    class Config:
        orm_mode = True


class ExtractionResultBase(BaseModel):
    """提取结果基础模式"""
    document_id: int
    extraction_time: datetime
    is_edited: bool
    last_edit_time: Optional[datetime] = None


class ExtractionResultResponse(ExtractionResultBase):
    """提取结果响应模式"""
    id: int
    groups: List[PhysicalStateGroupResponse] = []
    result_json: Dict[str, Any]

    class Config:
        orm_mode = True


class ExtractionResultEdit(BaseModel):
    """提取结果编辑模式"""
    groups: List[Dict[str, Any]]
    user_name: str
    user_id: Optional[int] = None 