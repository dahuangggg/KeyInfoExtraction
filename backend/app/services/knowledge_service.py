import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document


class KnowledgeBaseService:
    def __init__(self, db: Session):
        self.db = db

    def create_knowledge_item(self, category: str, key: str, value: Dict[str, Any], 
                             source_document_id: Optional[int] = None) -> KnowledgeBase:
        """
        创建新的知识库条目
        """
        # 检查源文档是否存在
        if source_document_id:
            document = self.db.query(Document).filter(Document.id == source_document_id).first()
            if not document:
                raise HTTPException(status_code=404, detail=f"源文档ID {source_document_id} 不存在")

        # 检查是否已存在相同类别和键的条目
        existing = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.category == category,
            KnowledgeBase.key == key
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail=f"类别 '{category}' 和键 '{key}' 的知识条目已存在")

        # 创建新条目
        knowledge_item = KnowledgeBase(
            category=category,
            key=key,
            value=json.dumps(value, ensure_ascii=False),
            source_document_id=source_document_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.db.add(knowledge_item)
        self.db.commit()
        self.db.refresh(knowledge_item)

        return knowledge_item

    def get_knowledge_item(self, item_id: int) -> Optional[KnowledgeBase]:
        """
        根据ID获取知识库条目
        """
        return self.db.query(KnowledgeBase).filter(KnowledgeBase.id == item_id).first()

    def get_knowledge_by_category_key(self, category: str, key: str) -> Optional[KnowledgeBase]:
        """
        根据类别和键获取知识库条目
        """
        return self.db.query(KnowledgeBase).filter(
            KnowledgeBase.category == category,
            KnowledgeBase.key == key
        ).first()

    def search_knowledge(self, query: str = None, category: str = None, 
                        skip: int = 0, limit: int = 100) -> List[KnowledgeBase]:
        """
        搜索知识库条目
        """
        db_query = self.db.query(KnowledgeBase)

        # 应用过滤条件
        if category:
            db_query = db_query.filter(KnowledgeBase.category == category)

        if query:
            # 在键和值中搜索
            db_query = db_query.filter(
                or_(
                    KnowledgeBase.key.ilike(f"%{query}%"),
                    KnowledgeBase.value.cast(str).ilike(f"%{query}%")
                )
            )

        # 应用分页
        return db_query.order_by(KnowledgeBase.updated_at.desc()).offset(skip).limit(limit).all()

    def update_knowledge_item(self, item_id: int, data: Dict[str, Any]) -> KnowledgeBase:
        """
        更新知识库条目
        """
        knowledge_item = self.get_knowledge_item(item_id)
        if not knowledge_item:
            raise HTTPException(status_code=404, detail=f"知识条目ID {item_id} 不存在")

        # 更新字段
        if "category" in data:
            knowledge_item.category = data["category"]
        if "key" in data:
            knowledge_item.key = data["key"]
        if "value" in data:
            knowledge_item.value = json.dumps(data["value"], ensure_ascii=False)
        if "source_document_id" in data:
            # 检查源文档是否存在
            if data["source_document_id"]:
                document = self.db.query(Document).filter(Document.id == data["source_document_id"]).first()
                if not document:
                    raise HTTPException(status_code=404, detail=f"源文档ID {data['source_document_id']} 不存在")
            knowledge_item.source_document_id = data["source_document_id"]

        knowledge_item.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(knowledge_item)

        return knowledge_item

    def delete_knowledge_item(self, item_id: int) -> bool:
        """
        删除知识库条目
        """
        knowledge_item = self.get_knowledge_item(item_id)
        if not knowledge_item:
            raise HTTPException(status_code=404, detail=f"知识条目ID {item_id} 不存在")

        self.db.delete(knowledge_item)
        self.db.commit()
        return True

    def get_categories(self) -> List[str]:
        """
        获取所有知识类别
        """
        result = self.db.query(KnowledgeBase.category).distinct().all()
        return [r[0] for r in result]

    def import_from_extraction(self, document_id: int, extraction_data: Dict[str, Any]) -> List[KnowledgeBase]:
        """
        从提取结果导入到知识库
        """
        imported_items = []

        # 处理物理状态分析数据
        for group in extraction_data.get("元器件物理状态分析", []):
            group_name = group.get("物理状态组", "")
            
            for item in group.get("物理状态项", []):
                state_name = item.get("物理状态名称", "")
                if not state_name:
                    continue
                
                # 创建知识条目
                try:
                    knowledge_item = self.create_knowledge_item(
                        category="物理状态",
                        key=f"{group_name}_{state_name}",
                        value={
                            "物理状态组": group_name,
                            "物理状态名称": state_name,
                            "典型物理状态值": item.get("典型物理状态值", ""),
                            "禁限用信息": item.get("禁限用信息", "无"),
                            "测试评语": item.get("测试评语", "")
                        },
                        source_document_id=document_id
                    )
                    imported_items.append(knowledge_item)
                except HTTPException as e:
                    # 如果条目已存在，跳过
                    if e.status_code == 400:
                        continue
                    raise

        return imported_items 