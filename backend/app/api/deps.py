from typing import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.extraction_service import InformationExtractionService

def get_db_session() -> Generator:
    """
    获取数据库会话依赖
    """
    return get_db()

def get_extraction_service(db: Session = Depends(get_db_session)) -> InformationExtractionService:
    """
    获取信息提取服务依赖
    """
    return InformationExtractionService(db) 