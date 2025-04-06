#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase

class KnowledgeBaseService:
    """知识库服务类，用于管理知识库条目"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_knowledge_item(self, physical_group_name: str, physical_state_name: str, test_item_name: Optional[str],
                             physical_state_value: Optional[str], risk_assessment: Optional[str], 
                             detailed_analysis: Optional[str], source: str, reference_id: Optional[int]) -> KnowledgeBase:
        """创建知识库条目"""
        
        # 检查是否已存在相同的条目
        existing = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.physical_group_name == physical_group_name,
            KnowledgeBase.physical_state_name == physical_state_name,
            KnowledgeBase.test_item_name == test_item_name,
            KnowledgeBase.physical_state_value == physical_state_value,
            KnowledgeBase.source == source
        ).first()
        
        if existing:
            return existing
        
        # 创建新条目
        knowledge_item = KnowledgeBase(
            physical_group_name=physical_group_name,
            physical_state_name=physical_state_name,
            test_item_name=test_item_name,
            physical_state_value=physical_state_value,
            risk_assessment=risk_assessment,
            detailed_analysis=detailed_analysis,
            source=source,
            reference_id=reference_id,
            import_time=datetime.now()
        )
        
        self.db.add(knowledge_item)
        self.db.commit()
        self.db.refresh(knowledge_item)
        
        return knowledge_item
    
    def get_knowledge_item(self, item_id: int) -> Optional[KnowledgeBase]:
        """获取知识库条目"""
        
        return self.db.query(KnowledgeBase).filter(KnowledgeBase.id == item_id).first()
    
    def get_knowledge_by_state(self, physical_group_name: str, physical_state_name: str, 
                              test_item_name: Optional[str] = None) -> List[KnowledgeBase]:
        """按物理状态搜索知识库条目"""
        
        query = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.physical_group_name == physical_group_name,
            KnowledgeBase.physical_state_name == physical_state_name
        )
        
        if test_item_name:
            query = query.filter(KnowledgeBase.test_item_name == test_item_name)
        
        return query.all()
    
    def search_knowledge(self, physical_group_name: Optional[str] = None, 
                        physical_state_name: Optional[str] = None,
                        test_item_name: Optional[str] = None,
                        source: Optional[str] = None,
                        risk_assessment: Optional[str] = None,
                        query: Optional[str] = None,
                        skip: int = 0, limit: int = 100) -> List[KnowledgeBase]:
        """搜索知识库条目"""
        
        # 构建查询
        db_query = self.db.query(KnowledgeBase)
        
        # 应用过滤条件
        if physical_group_name:
            db_query = db_query.filter(KnowledgeBase.physical_group_name == physical_group_name)
        
        if physical_state_name:
            db_query = db_query.filter(KnowledgeBase.physical_state_name == physical_state_name)
        
        if test_item_name:
            db_query = db_query.filter(KnowledgeBase.test_item_name == test_item_name)
        
        if source:
            db_query = db_query.filter(KnowledgeBase.source == source)
        
        if risk_assessment:
            db_query = db_query.filter(KnowledgeBase.risk_assessment == risk_assessment)
        
        # 全文搜索
        if query:
            search_term = f"%{query}%"
            db_query = db_query.filter(
                (KnowledgeBase.physical_group_name.ilike(search_term)) |
                (KnowledgeBase.physical_state_name.ilike(search_term)) |
                (KnowledgeBase.test_item_name.ilike(search_term)) |
                (KnowledgeBase.physical_state_value.ilike(search_term)) |
                (KnowledgeBase.detailed_analysis.ilike(search_term))
            )
        
        # 执行查询
        return db_query.order_by(KnowledgeBase.import_time.desc()).offset(skip).limit(limit).all()
    
    def update_knowledge_item(self, item_id: int, data: Dict[str, Any]) -> KnowledgeBase:
        """更新知识库条目"""
        
        knowledge_item = self.get_knowledge_item(item_id)
        if not knowledge_item:
            raise ValueError(f"知识库条目 {item_id} 不存在")
        
        # 更新字段
        if "physical_group_name" in data:
            knowledge_item.physical_group_name = data["physical_group_name"]
        
        if "physical_state_name" in data:
            knowledge_item.physical_state_name = data["physical_state_name"]
        
        if "test_item_name" in data:
            knowledge_item.test_item_name = data["test_item_name"]
        
        if "physical_state_value" in data:
            knowledge_item.physical_state_value = data["physical_state_value"]
        
        if "risk_assessment" in data:
            knowledge_item.risk_assessment = data["risk_assessment"]
        
        if "detailed_analysis" in data:
            knowledge_item.detailed_analysis = data["detailed_analysis"]
        
        knowledge_item.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(knowledge_item)
        
        return knowledge_item
    
    def delete_knowledge_item(self, item_id: int) -> bool:
        """删除知识库条目"""
        
        knowledge_item = self.get_knowledge_item(item_id)
        if not knowledge_item:
            return False
        
        self.db.delete(knowledge_item)
        self.db.commit()
        
        return True
    
    def get_physical_groups(self) -> List[str]:
        """获取所有物理状态组"""
        
        result = self.db.query(KnowledgeBase.physical_group_name).distinct().all()
        return [r[0] for r in result]
    
    def get_physical_states(self, physical_group_name: Optional[str] = None) -> List[str]:
        """获取物理状态名称"""
        
        query = self.db.query(KnowledgeBase.physical_state_name).distinct()
        
        if physical_group_name:
            query = query.filter(KnowledgeBase.physical_group_name == physical_group_name)
        
        result = query.all()
        return [r[0] for r in result]
    
    def get_test_items(self) -> List[str]:
        """获取所有试验项目"""
        
        result = self.db.query(KnowledgeBase.test_item_name).distinct().all()
        return [r[0] for r in result if r[0]]  # 排除None值
    
    def import_from_extraction(self, extraction_result_id: int, extraction_data: Dict[str, Any]) -> List[KnowledgeBase]:
        """从提取结果导入到知识库"""
        
        imported_items = []
        
        # 这里需要解析extraction_data并创建对应的知识库条目
        # 具体实现取决于extraction_data的结构
        if "元器件物理状态分析" in extraction_data:
            physical_state_analysis = extraction_data["元器件物理状态分析"]
            
            for group in physical_state_analysis:
                group_name = group.get("物理状态组", "")
                if not group_name:
                    continue
                
                for state_item in group.get("物理状态项", []):
                    state_name = state_item.get("物理状态名称", "")
                    if not state_name:
                        continue
                    
                    # 创建知识库条目
                    # 修正字段映射，正确获取数据
                    knowledge_item = self.create_knowledge_item(
                        physical_group_name=group_name,
                        physical_state_name=state_name,
                        test_item_name=state_item.get("试验项目", ""),  # 使用添加的试验项目字段
                        physical_state_value=state_item.get("典型物理状态值", ""),  # 使用典型物理状态值
                        risk_assessment=state_item.get("禁限用信息", ""),  # 使用禁限用信息
                        detailed_analysis=state_item.get("测试评语", ""),  # 使用测试评语
                        source="extraction",
                        reference_id=extraction_result_id
                    )
                    
                    imported_items.append(knowledge_item)
        
        return imported_items 