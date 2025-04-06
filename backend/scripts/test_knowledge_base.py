#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test_knowledge_base.py

import sys
import os
import logging
from sqlalchemy import text

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.knowledge_base import KnowledgeBase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_knowledge_base():
    """测试知识库模型"""
    
    try:
        db = SessionLocal()
        
        try:
            # 1. 检查表是否存在
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_base'"))
            tables = result.fetchall()
            
            if not tables:
                logger.info("知识库表不存在，将自动创建...")
                # 这里不需要做什么，因为表会在后续操作中自动创建
            else:
                logger.info("知识库表已存在")
            
            # 2. 创建测试记录
            test_item = KnowledgeBase(
                physical_group_name="测试组",
                physical_state_name="测试状态",
                test_item_name="测试项目",
                physical_state_value="测试值",
                risk_assessment="可用",
                detailed_analysis="这是一条测试记录",
                source="test",
                reference_id=None
            )
            
            db.add(test_item)
            db.commit()
            logger.info(f"创建测试记录成功，ID: {test_item.id}")
            
            # 3. 查询测试记录
            db_item = db.query(KnowledgeBase).filter(KnowledgeBase.id == test_item.id).first()
            if db_item:
                logger.info(f"查询测试记录成功: {db_item.physical_group_name} - {db_item.physical_state_name}")
            else:
                logger.error("查询测试记录失败")
            
            # 4. 删除测试记录
            db.delete(db_item)
            db.commit()
            logger.info("删除测试记录成功")
            
            logger.info("知识库模型测试完成，所有测试通过!")
            
        except Exception as e:
            db.rollback()
            logger.error(f"测试过程中发生错误: {str(e)}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("开始测试知识库模型...")
    test_knowledge_base() 