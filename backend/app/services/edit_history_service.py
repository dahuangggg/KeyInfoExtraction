from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.edit_history import EditHistory
from app.models.document import Document
from app.models.extraction import ExtractionResult, PhysicalStateGroup, PhysicalStateItem


class EditHistoryService:
    def __init__(self, db: Session):
        self.db = db

    def record_edit(self, document_id: int,
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

    def edit_extraction_result(self, document_id: int, edit_data: Dict[str, Any], 
                             extraction_service=None) -> Dict[str, Any]:
        """
        编辑提取结果并记录历史
        
        参数:
            document_id: 文档ID
            edit_data: 编辑数据
            extraction_service: 信息提取服务实例
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
                group_name = group_edit.get("物理状态组")
                
                # 查找物理状态组
                group = self.db.query(PhysicalStateGroup).filter(
                    PhysicalStateGroup.group_name == group_name,
                    PhysicalStateGroup.extraction_result_id == extraction_result.id
                ).first()
                
                # 如果组不存在，创建新组
                if not group:
                    group = PhysicalStateGroup(
                        extraction_result_id=extraction_result.id,
                        group_name=group_name
                    )
                    self.db.add(group)
                    self.db.flush()  # 获取ID
                
                # 处理物理状态项编辑
                if "物理状态项" in group_edit:
                    for item_edit in group_edit["物理状态项"]:
                        state_name = item_edit.get("物理状态名称")
                        
                        # 查找物理状态项
                        item = self.db.query(PhysicalStateItem).filter(
                            PhysicalStateItem.state_name == state_name,
                            PhysicalStateItem.physical_state_group_id == group.id
                        ).first()
                        
                        # 如果项不存在，创建新项
                        if not item:
                            item = PhysicalStateItem(
                                physical_state_group_id=group.id,
                                state_name=state_name
                            )
                            self.db.add(item)
                            self.db.flush()  # 获取ID
                        
                        # 编辑字段
                        fields_map = {
                            "典型物理状态值": "state_value",
                            "禁限用信息": "prohibition_info",
                            "测试评语": "test_comment"
                        }
                        
                        for display_name, field in fields_map.items():
                            if display_name in item_edit:
                                old_value = getattr(item, field)
                                new_value = item_edit[display_name]
                                
                                if old_value != new_value:
                                    # 记录编辑历史
                                    self.record_edit(
                                        document_id=document_id,
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
        
        # 重新构建结构化数据，更新result_json字段
        structured_info = {"元器件物理状态分析": []}
        
        # 查询所有物理状态组和项
        groups = self.db.query(PhysicalStateGroup).filter(
            PhysicalStateGroup.extraction_result_id == extraction_result.id
        ).all()
        
        for group in groups:
            group_info = {
                "物理状态组": group.group_name,
                "物理状态项": []
            }
            
            items = self.db.query(PhysicalStateItem).filter(
                PhysicalStateItem.physical_state_group_id == group.id
            ).all()
            
            for item in items:
                item_info = {
                    "物理状态名称": item.state_name,
                    "典型物理状态值": item.state_value,
                    "禁限用信息": item.prohibition_info or "",
                    "测试评语": item.test_comment or ""
                }
                group_info["物理状态项"].append(item_info)
            
            structured_info["元器件物理状态分析"].append(group_info)
        
        # 更新result_json字段
        extraction_result.result_json = json.dumps(structured_info, ensure_ascii=False)
        
        # 提交更改
        self.db.commit()
        
        # 返回更新后的提取结果
        if extraction_service:
            # 使用传入的提取服务实例
            return extraction_service.get_extraction_result(document_id)
        else:
            # 如果没有传入提取服务实例，尝试创建一个（不推荐，但作为后备方案）
            from app.services.extraction_service import InformationExtractionService
            from app.api.deps import get_llm_extractor
            
            # 获取 LLMExtractor 单例
            extractor = get_llm_extractor()
            
            # 创建包含数据库会话和提取器的服务实例
            temp_extraction_service = InformationExtractionService(db=self.db, extractor=extractor)
            return temp_extraction_service.get_extraction_result(document_id) 