import os
import shutil
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document


class DocumentService:
    def __init__(self, db: Session):
        self.db = db

    async def upload_document(self, file: UploadFile) -> Document:
        """
        上传文档并保存到数据库
        """
        # 检查文件类型
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。允许的类型: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # 生成唯一文件名
        unique_filename = f"{uuid4().hex}.{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 创建文档记录
        db_document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_type=file_ext,
            upload_time=datetime.now(),
            processed=False
        )

        self.db.add(db_document)
        self.db.commit()
        self.db.refresh(db_document)

        return db_document

    def get_document(self, document_id: int) -> Optional[Document]:
        """
        根据ID获取文档
        """
        return self.db.query(Document).filter(Document.id == document_id).first()

    def get_all_documents(self, skip: int = 0, limit: int = 100) -> List[Document]:
        """
        获取所有文档，支持分页
        """
        return self.db.query(Document).order_by(Document.upload_time.desc()).offset(skip).limit(limit).all()

    def mark_document_as_processed(self, document_id: int, processing_time: float) -> Document:
        """
        将文档标记为已处理
        """
        document = self.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        document.processed = True
        document.processing_time = processing_time
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete_document(self, document_id: int) -> bool:
        """
        删除文档及其关联数据
        """
        document = self.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        # 删除物理文件
        if os.path.exists(document.file_path):
            os.remove(document.file_path)

        # 删除数据库记录（级联删除会处理关联的提取结果和编辑历史）
        self.db.delete(document)
        self.db.commit()
        return True 