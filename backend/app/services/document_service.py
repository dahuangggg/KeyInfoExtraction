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
        上传单个文档并保存到数据库
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

    async def upload_documents(self, files: List[UploadFile]) -> List[Document]:
        """
        批量上传多个文档并保存到数据库
        
        参数：
            files: 要上传的多个文件
            
        返回：
            上传成功的文档列表
        """
        if not files:
            raise HTTPException(status_code=400, detail="未提供任何文件")
        
        uploaded_documents = []
        
        for file in files:
            try:
                # 复用单个文件上传的方法
                document = await self.upload_document(file)
                uploaded_documents.append(document)
            except Exception as e:
                # 记录错误但继续处理其他文件
                print(f"上传文件 {file.filename} 时出错: {str(e)}")
                # 如果希望一个文件失败就中止整个过程，可以在此抛出异常
                # raise HTTPException(status_code=500, detail=f"上传文件 {file.filename} 时出错: {str(e)}")
        
        if not uploaded_documents:
            raise HTTPException(status_code=500, detail="所有文件上传均失败")
            
        return uploaded_documents

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
        
        参数：
            document_id: 文档ID
            processing_time: 处理时间（秒）
        
        返回：
            更新后的文档对象
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
        
    def batch_delete_documents(self, document_ids: List[int]) -> dict:
        """
        批量删除多个文档及其关联数据
        
        参数：
            document_ids: 要删除的文档ID列表
            
        返回：
            包含成功删除数量和失败数量的字典
        """
        if not document_ids:
            raise HTTPException(status_code=400, detail="未提供任何文档ID")
            
        success_count = 0
        failed_count = 0
        failed_ids = []
        
        for doc_id in document_ids:
            try:
                document = self.get_document(doc_id)
                if not document:
                    failed_count += 1
                    failed_ids.append(doc_id)
                    continue
                    
                # 删除物理文件
                if os.path.exists(document.file_path):
                    os.remove(document.file_path)
                
                # 删除数据库记录
                self.db.delete(document)
                # 不要在这里commit，等全部处理完一次性提交
                success_count += 1
            except Exception as e:
                failed_count += 1
                failed_ids.append(doc_id)
                print(f"删除文档ID {doc_id} 时出错: {str(e)}")
        
        # 一次性提交所有更改
        if success_count > 0:
            self.db.commit()
            
        return {
            "total": len(document_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_ids": failed_ids
        }

    def get_document_content(self, document_id: int) -> dict:
        """
        获取文档的内容
        
        参数：
            document_id: 文档ID
            
        返回：
            包含文档内容的字典
        """
        document = self.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")
        
        # 从文件名中获取唯一ID（去除扩展名）
        filename_without_ext = os.path.splitext(document.filename)[0]
        
        # 构建可能的文件路径（_extracted.txt）
        content_file_path = os.path.join(settings.OUTPUT_DIR, "temp", f"{filename_without_ext}_extracted.txt")
        
        # 检查文件是否存在
        if not os.path.exists(content_file_path):
            # 尝试其他可能的文件名格式
            content_file_path = os.path.join(settings.OUTPUT_DIR, "temp", f"{document.original_filename.split('.')[0]}_extracted.txt")
            
        # 如果仍然找不到文件，返回错误
        if not os.path.exists(content_file_path):
            raise HTTPException(status_code=404, detail="文档内容文件未找到")
            
        # 读取文件内容
        try:
            with open(content_file_path, "r", encoding="utf-8") as file:
                content = file.read()
                
            return {
                "document_id": document_id,
                "filename": document.original_filename,
                "content": content
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取文档内容时出错: {str(e)}") 