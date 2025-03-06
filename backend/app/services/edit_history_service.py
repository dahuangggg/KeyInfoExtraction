from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.edit_history import EditHistory
from app.models.document import Document
from app.models.extraction import ExtractionResult, PhysicalStateGroup, PhysicalStateItem


class EditHistoryService:
    def __init__(self, db: Session):
        self.db = db

    def record_edit(self, document_id: int, user_id: Optional[int], user_name: str,
                   entity_type: str, entity_id: int, field_name: str,
                   old_value: str, new_value: str) -> EditHistory:
        """
        记录编辑历史
        """
        # 检查文档是否存在
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail=f"文档ID {document_id} 不存在")

        # 创建编辑历史记录
        edit_history = EditHistory(
            document_id=document_id,
            edit_time=datetime.now(),
            user_id=user_id,
            user_name=user_name,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value
        )

        self.db.add(edit_history)
        self.db.commit()
        self.db.refresh(edit_history)

        return edit_history

    def get_document_edit_history(self, document_id: int, skip: int = 0, limit: int = 100) -> List[EditHistory]:
        """
        获取文档的编辑历史
        """
        return self.db.query(EditHistory).filter(
            EditHistory.document_id == document_id
        ).order_by(EditHistory.edit_time.desc()).offset(skip).limit(limit).all()

    def edit_extraction_result(self, document_id: int, user_id: Optional[int], user_name: str,
                              edit_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        编辑提取结果并记录历史
        """
        # 获取提取结果
        extraction_result = self.db.query(ExtractionResult).filter(
            ExtractionResult.document_id == document_id
        ).first()

        if not extraction_result:
            raise HTTPException(status_code=404, detail=f"文档ID {document_id} 的提取结果不存在")

        # 处理编辑
        if "groups" in edit_data:
            for group_edit in edit_data["groups"]:
                group_id = group_edit.get("id")
                
                # 查找物理状态组
                group = self.db.query(PhysicalStateGroup).filter(
                    PhysicalStateGroup.id == group_id,
                    PhysicalStateGroup.extraction_result_id == extraction_result.id
                ).first()
                
                if not group:
                    continue
                
                # 编辑组名
                if "group_name" in group_edit:
                    old_value = group.group_name
                    new_value = group_edit["group_name"]
                    
                    if old_value != new_value:
                        # 记录编辑历史
                        self.record_edit(
                            document_id=document_id,
                            user_id=user_id,
                            user_name=user_name,
                            entity_type="PhysicalStateGroup",
                            entity_id=group.id,
                            field_name="group_name",
                            old_value=old_value,
                            new_value=new_value
                        )
                        
                        # 更新值
                        group.group_name = new_value
                
                # 处理物理状态项编辑
                if "items" in group_edit:
                    for item_edit in group_edit["items"]:
                        item_id = item_edit.get("id")
                        
                        # 查找物理状态项
                        item = self.db.query(PhysicalStateItem).filter(
                            PhysicalStateItem.id == item_id,
                            PhysicalStateItem.physical_state_group_id == group.id
                        ).first()
                        
                        if not item:
                            continue
                        
                        # 编辑字段
                        fields_map = {
                            "state_name": "物理状态名称",
                            "state_value": "典型物理状态值",
                            "prohibition_info": "禁限用信息",
                            "test_comment": "测试评语"
                        }
                        
                        for field, display_name in fields_map.items():
                            if field in item_edit:
                                old_value = getattr(item, field)
                                new_value = item_edit[field]
                                
                                if old_value != new_value:
                                    # 记录编辑历史
                                    self.record_edit(
                                        document_id=document_id,
                                        user_id=user_id,
                                        user_name=user_name,
                                        entity_type="PhysicalStateItem",
                                        entity_id=item.id,
                                        field_name=display_name,
                                        old_value=old_value or "",
                                        new_value=new_value or ""
                                    )
                                    
                                    # 更新值
                                    setattr(item, field, new_value)

        # 标记提取结果为已编辑
        extraction_result.is_edited = True
        extraction_result.last_edit_time = datetime.now()
        
        # 提交更改
        self.db.commit()
        
        # 返回更新后的提取结果
        from app.services.extraction_service import InformationExtractionService
        extraction_service = InformationExtractionService(self.db)
        return extraction_service.get_extraction_result(document_id) 