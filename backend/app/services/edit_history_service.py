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
        编辑提取结果并记录历史 - 直接覆盖原有数据
        
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

        # 记录完整的原始数据作为历史记录
        old_data = json.loads(extraction_result.result_json)
        
        # 1. 首先查询需要删除的物理状态组
        groups_to_delete = self.db.query(PhysicalStateGroup).filter(
            PhysicalStateGroup.extraction_result_id == extraction_result.id
        ).all()
        
        # 2. 删除每个组关联的物理状态项
        for group in groups_to_delete:
            self.db.query(PhysicalStateItem).filter(
                PhysicalStateItem.physical_state_group_id == group.id
            ).delete(synchronize_session=False)
        
        # 3. 删除物理状态组
        self.db.query(PhysicalStateGroup).filter(
            PhysicalStateGroup.extraction_result_id == extraction_result.id
        ).delete(synchronize_session=False)
        
        # 4. 添加新的物理状态组和物理状态项
        if "groups" in edit_data:
            for group_idx, group_edit in enumerate(edit_data["groups"]):
                group_name = group_edit.get("物理状态组")
                
                # 创建新的物理状态组
                group = PhysicalStateGroup(
                    extraction_result_id=extraction_result.id,
                    group_name=group_name
                )
                self.db.add(group)
                self.db.flush()  # 获取ID
                
                # 添加物理状态项
                if "物理状态项" in group_edit:
                    for item_idx, item_edit in enumerate(group_edit["物理状态项"]):
                        state_name = item_edit.get("物理状态名称")
                        
                        # 创建新的物理状态项
                        item = PhysicalStateItem(
                            physical_state_group_id=group.id,
                            state_name=state_name,
                            state_value=item_edit.get("典型物理状态值", ""),
                            prohibition_info=item_edit.get("禁限用信息", ""),
                            test_comment=item_edit.get("测试评语", ""),
                            test_project=item_edit.get("试验项目", "")
                        )
                        self.db.add(item)
                        self.db.flush()  # 确保获取ID
                        
                        # 记录编辑历史 - 为每个字段创建一条记录
                        field_map = {
                            "典型物理状态值": "state_value",
                            "禁限用信息": "prohibition_info",
                            "测试评语": "test_comment",
                            "试验项目": "test_project"
                        }
                        
                        # 查找原始数据中对应的值
                        old_value = {}
                        if "元器件物理状态分析" in old_data:
                            for old_group in old_data["元器件物理状态分析"]:
                                if old_group.get("物理状态组") == group_name:
                                    for old_item in old_group.get("物理状态项", []):
                                        if old_item.get("物理状态名称") == state_name:
                                            old_value = old_item
                                            break
                        
                        # 记录编辑历史
                        for field_display, field_db in field_map.items():
                            new_val = item_edit.get(field_display, "")
                            old_val = old_value.get(field_display, "") if old_value else ""
                            
                            if new_val != old_val:
                                self.record_edit(
                                    document_id=document_id,
                                    entity_type="PhysicalStateItem",
                                    entity_id=item.id,
                                    field_name=field_display,
                                    old_value=old_val,
                                    new_value=new_val
                                )

        # 3. 直接更新result_json字段为新数据
        extraction_result.result_json = json.dumps({"元器件物理状态分析": edit_data["groups"]}, ensure_ascii=False)
        
        # 标记提取结果为已编辑
        extraction_result.is_edited = True
        extraction_result.last_edit_time = datetime.now()
        
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

    def revert_to_history_point(self, document_id: int, history_id: int, 
                               extraction_service=None) -> Dict[str, Any]:
        """
        回溯到特定历史点的文档状态
        
        参数:
            document_id: 文档ID
            history_id: 编辑历史ID
            extraction_service: 信息提取服务实例（可选）
            
        返回:
            回溯后的提取结果
        """
        # 检查文档是否存在
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail=f"文档ID {document_id} 不存在")
            
        # 获取目标历史记录
        target_history = self.db.query(EditHistory).filter(
            EditHistory.id == history_id,
            EditHistory.document_id == document_id
        ).first()
        
        if not target_history:
            raise HTTPException(status_code=404, detail=f"历史记录ID {history_id} 不存在或不属于文档 {document_id}")
            
        # 获取提取结果
        extraction_result = self.db.query(ExtractionResult).filter(
            ExtractionResult.document_id == document_id
        ).first()
        
        if not extraction_result:
            raise HTTPException(status_code=404, detail=f"文档ID {document_id} 的提取结果不存在")
            
        # 获取所有在目标历史记录之后的编辑历史（按时间从最近到最远排序）
        later_edits = self.db.query(EditHistory).filter(
            EditHistory.document_id == document_id,
            EditHistory.edit_time >= target_history.edit_time
        ).order_by(EditHistory.edit_time.desc()).all()
        
        # 对每个编辑记录进行回溯操作
        for edit in later_edits:
            # 根据实体类型和ID获取相应的实体
            if edit.entity_type == "PhysicalStateItem":
                item = self.db.query(PhysicalStateItem).filter(
                    PhysicalStateItem.id == edit.entity_id
                ).first()
                
                if item:
                    # 将字段映射回数据库字段名
                    field_map = {
                        "典型物理状态值": "state_value",
                        "禁限用信息": "prohibition_info",
                        "测试评语": "test_comment",
                        "试验项目": "test_project"
                    }
                    
                    db_field = field_map.get(edit.field_name)
                    if db_field:
                        # 回溯为旧值
                        setattr(item, db_field, edit.old_value)
        
        # 删除目标历史记录及其之后的所有历史记录
        self.db.query(EditHistory).filter(
            EditHistory.document_id == document_id,
            EditHistory.edit_time >= target_history.edit_time
        ).delete()
            
        # 标记提取结果为已编辑和回溯状态
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
                    "测试评语": item.test_comment or "",
                    "试验项目": item.test_project or ""
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
            # 如果没有传入提取服务实例，尝试创建一个
            from app.services.extraction_service import InformationExtractionService
            from app.api.deps import get_llm_extractor
            
            # 获取 LLMExtractor 单例
            extractor = get_llm_extractor()
            
            # 创建包含数据库会话和提取器的服务实例
            temp_extraction_service = InformationExtractionService(db=self.db, extractor=extractor)
            return temp_extraction_service.get_extraction_result(document_id) 