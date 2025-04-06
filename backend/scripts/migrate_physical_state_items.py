#!/usr/bin/env python
# -*- coding: utf-8 -*-
# migrate_physical_state_items.py

import sys
import os
import logging
import sqlite3

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_physical_state_items():
    """为physical_state_items表添加test_project列"""
    
    # 获取数据库路径
    db_path = settings.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
    # 如果路径以./开头，去掉./
    if db_path.startswith('./'):
        db_path = db_path[2:]
    logger.info(f"数据库路径: {db_path} (相对于当前工作目录)")
    
    # 获取当前工作目录
    current_dir = os.getcwd()
    logger.info(f"当前工作目录: {current_dir}")
    
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
            logger.info(f"physical_state_items表的当前列: {column_names}")
            
            if "test_project" not in column_names:
                logger.info("添加test_project列")
                cursor.execute("ALTER TABLE physical_state_items ADD COLUMN test_project TEXT")
                conn.commit()
                logger.info("成功添加test_project列")
            else:
                logger.info("test_project列已存在")
        else:
            logger.warning("physical_state_items表不存在")
            
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()
    
    logger.info("physical_state_items表迁移完成!")

if __name__ == "__main__":
    migrate_physical_state_items() 