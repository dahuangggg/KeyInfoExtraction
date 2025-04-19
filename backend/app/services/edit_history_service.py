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
        
        # 处理删除操作已经移到前端，这部分代码不再需要
        # 现在前端会直接发送正确格式的groups数据
        
        # 只有在有groups字段时才继续处理常规更新
        if "groups" in edit_data:
            # 先提取旧数据中的物理状态项
            old_physical_items = []
            if "元器件物理状态分析" in old_data:
                for old_group in old_data["元器件物理状态分析"]:
                    group_name = old_group.get("物理状态组", "")
                    for old_item in old_group.get("物理状态项", []):
                        old_physical_items.append({
                            "物理状态组": group_name,
                            "物理状态名称": old_item.get("物理状态名称", ""),
                            "典型物理状态值": old_item.get("典型物理状态值", ""),
                            "禁限用信息": old_item.get("禁限用信息", ""),
                            "测试评语": old_item.get("测试评语", ""),
                            "试验项目": old_item.get("试验项目", "")
                        })
            
            # 提取新数据中的物理状态项
            new_physical_items = []
            for new_group in edit_data["groups"]:
                group_name = new_group.get("物理状态组", "")
                for new_item in new_group.get("物理状态项", []):
                    new_physical_items.append({
                        "物理状态组": group_name,
                        "物理状态名称": new_item.get("物理状态名称", ""),
                        "典型物理状态值": new_item.get("典型物理状态值", ""),
                        "禁限用信息": new_item.get("禁限用信息", ""),
                        "测试评语": new_item.get("测试评语", ""),
                        "试验项目": new_item.get("试验项目", "")
                    })
            
            # 查找并保存删除操作的记录列表，但暂不立即记录到数据库
            deleted_items_info = []
            
            # 查找删除的物理状态项（在旧数据中存在但在新数据中不存在）
            for old_item in old_physical_items:
                found = False
                for new_item in new_physical_items:
                    if (old_item["物理状态组"] == new_item["物理状态组"] and 
                        old_item["物理状态名称"] == new_item["物理状态名称"]):
                        found = True
                        break
                
                if not found:
                    # 尝试查找对应的数据库记录
                    deleted_item = None
                    group = self.db.query(PhysicalStateGroup).filter(
                        PhysicalStateGroup.extraction_result_id == extraction_result.id,
                        PhysicalStateGroup.group_name == old_item["物理状态组"]
                    ).first()
                    
                    if group:
                        deleted_item = self.db.query(PhysicalStateItem).filter(
                            PhysicalStateItem.physical_state_group_id == group.id,
                            PhysicalStateItem.state_name == old_item["物理状态名称"]
                        ).first()
                    
                    if deleted_item:
                        # 将删除信息保存到列表中，供后续记录
                        print(f"检测到删除操作: {old_item['物理状态组']} / {old_item['物理状态名称']}")
                        deleted_items_info.append({
                            "entity_id": deleted_item.id,
                            "old_value": json.dumps(old_item, ensure_ascii=False)
                        })
            
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
            added_items_info = []  # 保存新增条目信息
            edited_items_info = []  # 保存编辑条目信息
            
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
                        
                        # 定义字段映射
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
                        
                        # 收集新增条目信息
                        if not old_value:  # 如果是新添加的条目
                            added_items_info.append({
                                "entity_id": item.id,
                                "state_name": state_name
                            })
                        else:
                            # 对于编辑的条目，检查是否有字段发生变化
                            has_changes = False
                            for field_display, field_db in field_map.items():
                                new_val = item_edit.get(field_display, "")
                                old_val = old_value.get(field_display, "") if old_value else ""
                                if new_val != old_val:
                                    has_changes = True
                                    break
                            
                            # 收集编辑条目信息
                            if has_changes:
                                # 构造完整的旧值
                                complete_old_value = {
                                    "物理状态名称": old_value.get("物理状态名称", ""),
                                    "典型物理状态值": old_value.get("典型物理状态值", ""),
                                    "禁限用信息": old_value.get("禁限用信息", ""),
                                    "测试评语": old_value.get("测试评语", ""),
                                    "试验项目": old_value.get("试验项目", "")
                                }
                                
                                # 构造完整的新值
                                complete_new_value = {
                                    "物理状态名称": item_edit.get("物理状态名称", ""),
                                    "典型物理状态值": item_edit.get("典型物理状态值", ""),
                                    "禁限用信息": item_edit.get("禁限用信息", ""),
                                    "测试评语": item_edit.get("测试评语", ""),
                                    "试验项目": item_edit.get("试验项目", "")
                                }
                                
                                edited_items_info.append({
                                    "entity_id": item.id,
                                    "old_value": json.dumps(complete_old_value, ensure_ascii=False),
                                    "new_value": json.dumps(complete_new_value, ensure_ascii=False)
                                })

            # 3. 直接更新result_json字段为新数据
            extraction_result.result_json = json.dumps({"元器件物理状态分析": edit_data["groups"]}, ensure_ascii=False)
            
            # 更新操作历史记录 - 只有在数据库操作成功后才记录历史
            
            # 记录删除操作
            for deleted_item in deleted_items_info:
                # 保存完整的物理状态项信息，而不仅仅是名称
                self.record_edit(
                    document_id=document_id,
                    entity_type="PhysicalStateItem",
                    entity_id=deleted_item["entity_id"],
                    field_name="删除条目",  # 修改类型显示为"删除条目"
                    old_value=deleted_item["old_value"],  # 保存完整的物理状态项信息JSON
                    new_value=""  # 修改值为空
                )
            
            # 记录新增操作
            for added_item in added_items_info:
                self.record_edit(
                    document_id=document_id,
                    entity_type="PhysicalStateItem",
                    entity_id=added_item["entity_id"],
                    field_name="添加条目",  # 修改类型显示为"添加条目"
                    old_value="",  # 原值为空
                    new_value=added_item["state_name"]  # 修改值为添加条目的物理状态名
                )
            
            # 记录编辑操作
            for edited_item in edited_items_info:
                # 解析旧值和新值
                old_data = json.loads(edited_item["old_value"])
                new_data = json.loads(edited_item["new_value"])
                
                # 对比各个字段，找出变化的字段并记录
                field_map = {
                    "物理状态名称": "物理状态名称",
                    "典型物理状态值": "典型物理状态值",
                    "禁限用信息": "风险评价",
                    "测试评语": "测试评语",
                    "试验项目": "试验项目"
                }
                
                for field_key, display_name in field_map.items():
                    old_val = old_data.get(field_key, "")
                    new_val = new_data.get(field_key, "")
                    
                    # 只记录发生变化的字段
                    if old_val != new_val:
                        self.record_edit(
                            document_id=document_id,
                            entity_type="PhysicalStateItem",
                            entity_id=edited_item["entity_id"],
                            field_name=display_name,  # 修改类型显示为对应字段名称
                            old_value=old_val,  # 原值为修改前的值
                            new_value=new_val   # 修改值为修改后的值
                        )
        
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
        print(f"开始回溯文档 {document_id} 的历史记录 {history_id}")
        
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
            
        print(f"找到目标历史记录: {target_history.id}, 类型: {target_history.entity_type}, 字段: {target_history.field_name}")
            
        # 获取提取结果
        extraction_result = self.db.query(ExtractionResult).filter(
            ExtractionResult.document_id == document_id
        ).first()
        
        if not extraction_result:
            raise HTTPException(status_code=404, detail=f"文档ID {document_id} 的提取结果不存在")
            
        # 获取所有在目标历史记录之后的编辑历史（按时间从最晚到最早排序）
        later_edits = self.db.query(EditHistory).filter(
            EditHistory.document_id == document_id,
            EditHistory.edit_time >= target_history.edit_time
        ).order_by(EditHistory.edit_time.desc()).all()
        
        print(f"找到 {len(later_edits)} 条需要回溯的历史记录")
        if later_edits:
            print(f"历史记录时间范围: {later_edits[-1].edit_time} - {later_edits[0].edit_time}")
            # 输出每条历史记录的信息，帮助调试
            for i, edit in enumerate(later_edits):
                print(f"历史记录[{i}]: ID={edit.id}, 时间={edit.edit_time}, 类型={edit.entity_type}, 字段={edit.field_name}")
        
        # 对每个编辑记录进行回溯操作
        for edit in later_edits:
            print(f"处理历史记录: {edit.id}, 类型: {edit.entity_type}, 字段: {edit.field_name}")
            
            # 根据实体类型和ID获取相应的实体
            if edit.entity_type == "PhysicalStateItem":
                item = self.db.query(PhysicalStateItem).filter(
                    PhysicalStateItem.id == edit.entity_id
                ).first()
                
                # 处理删除条目操作
                if edit.field_name == "删除条目":
                    # 这是删除操作的撤销，需要恢复被删除的条目
                    if item:
                        print(f"检测到删除操作撤销，找到物理状态项: {item.id}, 状态名称: {item.state_name}")
                    else:
                        print(f"检测到删除操作撤销，物理状态项已被删除，entity_id: {edit.entity_id}")
                    
                    # 尝试从历史记录中恢复被删除的条目
                    try:
                        # 解析旧值数据，获取完整的物理状态项信息
                        try:
                            complete_item_data = json.loads(edit.old_value)
                            if not isinstance(complete_item_data, dict):
                                raise ValueError("旧值不是有效的JSON对象")
                        except Exception as e:
                            print(f"解析旧值JSON失败: {e}，尝试其他方式恢复")
                            # 如果JSON解析失败，尝试使用旧值作为物理状态名
                            complete_item_data = {
                                "物理状态名称": edit.old_value,
                                "物理状态组": "未分类",
                                "典型物理状态值": "",
                                "禁限用信息": "",
                                "测试评语": "",
                                "试验项目": ""
                            }
                        
                        # 提取必要信息
                        state_name = complete_item_data.get("物理状态名称", "")
                        group_name = complete_item_data.get("物理状态组", "未分类")
                        
                        print(f"从历史记录中获取到的信息: 物理状态名={state_name}, 组名={group_name}")
                        
                        # 检查物理状态组是否存在
                        group = self.db.query(PhysicalStateGroup).filter(
                            PhysicalStateGroup.extraction_result_id == extraction_result.id,
                            PhysicalStateGroup.group_name == group_name
                        ).first()
                        
                        if not group:
                            # 如果组不存在，创建新组
                            print(f"物理状态组 '{group_name}' 不存在，创建新组")
                            group = PhysicalStateGroup(
                                extraction_result_id=extraction_result.id,
                                group_name=group_name
                            )
                            self.db.add(group)
                            self.db.flush()  # 获取ID
                        
                        # 检查是否已存在相同物理状态名的项
                        existing_item = self.db.query(PhysicalStateItem).filter(
                            PhysicalStateItem.physical_state_group_id == group.id,
                            PhysicalStateItem.state_name == state_name
                        ).first()
                        
                        if not existing_item:
                            # 创建新的物理状态项，恢复所有字段
                            new_item = PhysicalStateItem(
                                physical_state_group_id=group.id,
                                state_name=state_name,
                                state_value=complete_item_data.get("典型物理状态值", ""),
                                prohibition_info=complete_item_data.get("禁限用信息", ""),
                                test_comment=complete_item_data.get("测试评语", ""),
                                test_project=complete_item_data.get("试验项目", "")
                            )
                            self.db.add(new_item)
                            self.db.flush()
                            print(f"成功恢复删除的物理状态项: {state_name}，ID: {new_item.id}，包含所有字段值")
                        else:
                            print(f"物理状态项 '{state_name}' 已存在，ID: {existing_item.id}")
                    except Exception as e:
                        print(f"恢复删除条目时出错: {e}")
                        import traceback
                        traceback.print_exc()
                
                # 处理添加条目操作
                elif edit.field_name == "添加条目" and item:
                    # 这是新增操作的撤销，需要删除条目
                    print(f"撤销添加条目操作，将删除条目: {item.id}, 状态名称: {item.state_name}")
                    # 先找到这个物理状态项所属的组
                    group = self.db.query(PhysicalStateGroup).filter(
                        PhysicalStateGroup.id == item.physical_state_group_id
                    ).first()
                    
                    # 检查组是否存在
                    if group:
                        print(f"找到物理状态组: {group.id}, 组名: {group.group_name}")
                        
                        # 删除物理状态项
                        self.db.delete(item)
                        print(f"已删除物理状态项: {item.id}")
                        
                        # 检查组内是否还有其他物理状态项
                        other_items = self.db.query(PhysicalStateItem).filter(
                            PhysicalStateItem.physical_state_group_id == group.id,
                            PhysicalStateItem.id != item.id
                        ).count()
                        
                        print(f"组内剩余物理状态项数量: {other_items}")
                        
                        # 如果组内没有其他物理状态项了，也删除组
                        if other_items == 0:
                            self.db.delete(group)
                            print(f"已删除空物理状态组: {group.id}")
                        
                        # 立即提交更改，确保后续查询能看到最新状态
                        self.db.flush()
                
                # 处理字段修改操作
                elif item and edit.field_name in ["物理状态名称", "典型物理状态值", "风险评价", "测试评语", "试验项目"]:
                    # 将显示字段名映射回数据库字段名
                    field_map = {
                        "物理状态名称": "state_name",
                        "典型物理状态值": "state_value",
                        "风险评价": "prohibition_info",
                        "测试评语": "test_comment",
                        "试验项目": "test_project"
                    }
                    
                    db_field = field_map.get(edit.field_name)
                    if db_field:
                        old_value = getattr(item, db_field)
                        # 回溯为旧值
                        setattr(item, db_field, edit.old_value)
                        print(f"已更新字段 {edit.field_name}: '{old_value}' -> '{edit.old_value}'")
                        # 立即提交更改
                        self.db.flush()

        # 删除目标历史记录及其之后的所有历史记录
        deleted_count = self.db.query(EditHistory).filter(
            EditHistory.document_id == document_id,
            EditHistory.edit_time >= target_history.edit_time
        ).delete()
        print(f"已删除 {deleted_count} 条历史记录")
            
        # 标记提取结果为已编辑和回溯状态
        extraction_result.is_edited = True
        extraction_result.last_edit_time = datetime.now()
        
        # 重新构建结构化数据，更新result_json字段
        structured_info = {"元器件物理状态分析": []}
        
        # 查询所有物理状态组和项
        groups = self.db.query(PhysicalStateGroup).filter(
            PhysicalStateGroup.extraction_result_id == extraction_result.id
        ).all()
        
        print(f"重建结构化数据，找到 {len(groups)} 个物理状态组")
        
        for group in groups:
            group_info = {
                "物理状态组": group.group_name,
                "物理状态项": []
            }
            
            items = self.db.query(PhysicalStateItem).filter(
                PhysicalStateItem.physical_state_group_id == group.id
            ).all()
            
            print(f"物理状态组 '{group.group_name}' 包含 {len(items)} 个物理状态项")
            
            for item in items:
                item_info = {
                    "物理状态名称": item.state_name,
                    "典型物理状态值": item.state_value,
                    "禁限用信息": item.prohibition_info or "",
                    "测试评语": item.test_comment or "",
                    "试验项目": item.test_project or ""
                }
                group_info["物理状态项"].append(item_info)
            
            # 只有当组内有物理状态项时才添加到结果中
            if group_info["物理状态项"]:
                structured_info["元器件物理状态分析"].append(group_info)
        
        # 更新result_json字段
        old_json = extraction_result.result_json
        extraction_result.result_json = json.dumps(structured_info, ensure_ascii=False)
        print(f"已更新result_json字段，旧值长度: {len(old_json) if old_json else 0}，新值长度: {len(extraction_result.result_json)}")
        
        # 提交更改
        self.db.commit()
        print(f"回溯完成，已提交所有更改")
        
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