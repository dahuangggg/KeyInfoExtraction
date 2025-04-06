#!/usr/bin/env python
# -*- coding: utf-8 -*-
# migrate_knowledge_base.py

import sys
import os
import logging
import sqlite3
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_knowledge_base(db_path):
    """迁移知识库表结构"""
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_base'")
        if cursor.fetchone():
            logger.info("找到现有的知识库表，准备更新表结构...")
            
            # 创建新表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                physical_group_name VARCHAR(255) NOT NULL,
                physical_state_name VARCHAR(255) NOT NULL,
                test_item_name VARCHAR(255),
                physical_state_value TEXT,
                risk_assessment VARCHAR(50),
                detailed_analysis TEXT,
                source VARCHAR(20) NOT NULL,
                reference_id INTEGER,
                import_time TIMESTAMP,
                updated_at TIMESTAMP
            )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_physical_group_name ON knowledge_base_new (physical_group_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_physical_state_name ON knowledge_base_new (physical_state_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_test_item_name ON knowledge_base_new (test_item_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_source ON knowledge_base_new (source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_reference_id ON knowledge_base_new (reference_id)")
            
            # 尝试从旧表迁移数据
            try:
                # 获取旧表列信息
                cursor.execute("PRAGMA table_info(knowledge_base)")
                old_columns = cursor.fetchall()
                old_column_names = [col[1] for col in old_columns]
                
                logger.info(f"旧表列: {old_column_names}")
                
                if 'category' in old_column_names and 'key' in old_column_names and 'value' in old_column_names:
                    logger.info("尝试从旧格式迁移数据...")
                    
                    # 查询旧表数据
                    cursor.execute("SELECT id, category, key, value, created_at, updated_at FROM knowledge_base")
                    old_data = cursor.fetchall()
                    
                    # 迁移数据到新表
                    migrated_count = 0
                    for row in old_data:
                        try:
                            # 这里需要根据实际情况进行数据转换
                            # 这里假设category对应physical_group_name，key对应physical_state_name
                            cursor.execute("""
                            INSERT INTO knowledge_base_new 
                            (id, physical_group_name, physical_state_name, source, import_time, updated_at)
                            VALUES (?, ?, ?, 'migrated', ?, ?)
                            """, (row[0], row[1], row[2], row[4], row[5]))
                            migrated_count += 1
                        except Exception as e:
                            logger.warning(f"迁移记录时发生错误: {str(e)}")
                            continue
                    
                    logger.info(f"成功迁移 {migrated_count}/{len(old_data)} 条记录")
            except Exception as e:
                logger.warning(f"尝试迁移数据时发生错误: {str(e)}")
                logger.info("将不迁移数据，仅创建新表结构")
            
            # 备份旧表并替换为新表
            cursor.execute("ALTER TABLE knowledge_base RENAME TO knowledge_base_old")
            cursor.execute("ALTER TABLE knowledge_base_new RENAME TO knowledge_base")
            
            conn.commit()
            logger.info("知识库表结构更新完成")
            
        else:
            logger.info("知识库表不存在，创建新表...")
            
            # 创建知识库表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                physical_group_name VARCHAR(255) NOT NULL,
                physical_state_name VARCHAR(255) NOT NULL,
                test_item_name VARCHAR(255),
                physical_state_value TEXT,
                risk_assessment VARCHAR(50),
                detailed_analysis TEXT,
                source VARCHAR(20) NOT NULL,
                reference_id INTEGER,
                import_time TIMESTAMP,
                updated_at TIMESTAMP
            )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_physical_group_name ON knowledge_base (physical_group_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_physical_state_name ON knowledge_base (physical_state_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_test_item_name ON knowledge_base (test_item_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_source ON knowledge_base (source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_reference_id ON knowledge_base (reference_id)")
            
            conn.commit()
            logger.info("知识库表创建完成")
        
        # 检查并删除旧的映射表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_base_mapping'")
        if cursor.fetchone():
            logger.info("检测到旧的知识库映射表，执行删除操作...")
            cursor.execute("DROP TABLE knowledge_base_mapping")
            conn.commit()
            logger.info("知识库映射表删除完成")
        else:
            logger.info("知识库映射表不存在，无需处理")
            
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {str(e)}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

def migrate_database():
    """迁移数据库结构"""
    
    # 获取数据库路径
    db_path = settings.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
    logger.info(f"数据库路径: {db_path}")
    
    # 连接到SQLite数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查physical_state_items表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='physical_state_items'")
        if cursor.fetchone():
            logger.info("找到physical_state_items表")
            
            # 检查test_project列是否存在
            cursor.execute("PRAGMA table_info(physical_state_items)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            if "test_project" not in column_names:
                logger.info("添加test_project列")
                cursor.execute("ALTER TABLE physical_state_items ADD COLUMN test_project TEXT")
                conn.commit()
                logger.info("成功添加test_project列")
            else:
                logger.info("test_project列已存在")
        else:
            logger.warning("physical_state_items表不存在")
        
        # 检查knowledge_base表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_base'")
        if cursor.fetchone():
            logger.info("找到knowledge_base表，确认结构")
        else:
            logger.warning("knowledge_base表不存在，将由应用程序自动创建")
            
        # 检查并删除knowledge_base_mapping表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_base_mapping'")
        if cursor.fetchone():
            logger.info("检测到知识库映射表，执行删除操作...")
            cursor.execute("DROP TABLE knowledge_base_mapping")
            conn.commit()
            logger.info("知识库映射表删除完成")
        else:
            logger.info("知识库映射表不存在，无需处理")
            
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()
    
    logger.info("数据库迁移完成!")

def main():
    """主函数"""
    
    # 获取数据库路径
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "key_info_extraction.db"  # 默认路径
    
    logger.info(f"开始迁移知识库表结构，数据库路径: {db_path}")
    migrate_knowledge_base(db_path)
    logger.info("迁移完成")

if __name__ == "__main__":
    migrate_database() 