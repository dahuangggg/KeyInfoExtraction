#!/usr/bin/env python
# -*- coding: utf-8 -*-
# import_knowledge_base.py

import json
import os
import sys
import logging
import argparse
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.knowledge_base import KnowledgeBase
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_format_json_to_knowledge_base(json_file_path, dry_run=False, skip_duplicates=True):
    """从format.json导入数据到知识库"""
    
    try:
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 创建数据库会话
        db = SessionLocal()
        
        # 记录导入统计
        total_items = len(data)
        imported_items = 0
        skipped_items = 0
        duplicate_items = 0
        
        # 如果是dry_run模式，则只打印即将导入的数据，不实际导入
        if dry_run:
            logger.info(f"DRY-RUN模式: 将模拟导入 {total_items} 条记录，但不实际写入数据库")
            for i, item in enumerate(data[:5]):  # 只显示前5条
                logger.info(f"样例{i+1}: {item.get('物理状态组', '')} - {item.get('物理状态', '')} - {item.get('物理状态值', '')}")
            if total_items > 5:
                logger.info(f"... 还有 {total_items - 5} 条记录")
            logger.info(f"DRY-RUN完成，共有 {total_items} 条记录待导入")
            return {
                "status": "success",
                "total": total_items,
                "imported": 0,
                "skipped": 0,
                "duplicates": 0,
                "dry_run": True
            }
        
        try:
            # 批量导入数据
            for item in data:
                # 检查是否存在相同条目
                if skip_duplicates:
                    existing = db.query(KnowledgeBase).filter(
                        KnowledgeBase.physical_group_name == item.get("物理状态组", ""),
                        KnowledgeBase.physical_state_name == item.get("物理状态", ""),
                        KnowledgeBase.test_item_name == item.get("试验项目", ""),
                        KnowledgeBase.physical_state_value == item.get("物理状态值", ""),
                        KnowledgeBase.source == "standard"
                    ).first()
                    
                    if existing:
                        duplicate_items += 1
                        continue
                
                # 创建知识库条目
                knowledge_item = KnowledgeBase(
                    physical_group_name=item.get("物理状态组", ""),
                    physical_state_name=item.get("物理状态", ""),
                    test_item_name=item.get("试验项目", ""),
                    physical_state_value=item.get("物理状态值", ""),
                    risk_assessment=item.get("风险评价", ""),
                    detailed_analysis=item.get("详细分析", ""),
                    source="standard",  # 标记为标准库来源
                    reference_id=None,  # 标准库无引用ID
                    import_time=datetime.now()
                )
                
                try:
                    # 添加到数据库
                    db.add(knowledge_item)
                    db.flush()  # 刷新以获取ID，但不提交
                    imported_items += 1
                    
                    # 每100条提交一次，减轻数据库压力
                    if imported_items % 100 == 0:
                        db.commit()
                        logger.info(f"已导入 {imported_items}/{total_items} 条记录")
                        
                except IntegrityError:
                    # 如果有重复项，回滚并跳过
                    db.rollback()
                    skipped_items += 1
                    logger.warning(f"跳过重复项: {item.get('物理状态组')} - {item.get('物理状态')} - {item.get('物理状态值')}")
                    continue
            
            # 提交剩余的记录
            db.commit()
            logger.info(f"导入完成! 总计: {total_items}, 导入: {imported_items}, 跳过: {skipped_items}, 重复: {duplicate_items}")
            
            return {
                "status": "success",
                "total": total_items,
                "imported": imported_items,
                "skipped": skipped_items,
                "duplicates": duplicate_items,
                "dry_run": False
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"导入过程中发生错误: {str(e)}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"导入失败: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

def main():
    """主函数"""
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='从format.json导入数据到知识库')
    parser.add_argument('file', metavar='FILE', help='format.json文件路径')
    parser.add_argument('--dry-run', action='store_true', help='仅模拟导入，不实际写入数据库')
    parser.add_argument('--force', action='store_true', help='强制导入，即使有重复项')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 获取文件路径
    json_file_path = args.file
    
    # 检查文件是否存在
    if not os.path.exists(json_file_path):
        logger.error(f"文件不存在: {json_file_path}")
        sys.exit(1)
    
    logger.info(f"开始从 {json_file_path} 导入知识库数据...")
    result = import_format_json_to_knowledge_base(
        json_file_path, 
        dry_run=args.dry_run,
        skip_duplicates=not args.force
    )
    
    # 检查导入结果
    if result["status"] == "error":
        logger.error(f"导入失败: {result['error']}")
        sys.exit(1)
    
    if result["dry_run"]:
        logger.info("DRY-RUN模式完成，未实际导入数据")
    else:
        logger.info(f"导入成功! 总计: {result['total']}, 导入: {result['imported']}, "
                   f"跳过: {result['skipped']}, 重复: {result['duplicates']}")

if __name__ == "__main__":
    main() 