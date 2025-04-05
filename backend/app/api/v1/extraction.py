from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
import os
import tempfile
import json
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.deps import get_db_session, get_extraction_service
from app.services.extraction_service import InformationExtractionService
from app.services.edit_history_service import EditHistoryService
from app.schemas.extraction import ExtractionResultResponse, ExtractionResultEdit
from app.models.document import Document
from app.core.config import settings
from app.utils import save_excel

router = APIRouter()


@router.post("", response_model=Dict[str, Any])
async def create_extraction(
    document_id: int,
    background_tasks: BackgroundTasks,
    extraction_service: InformationExtractionService = Depends(get_extraction_service),
    db: Session = Depends(get_db_session)
):
    """
    创建一个提取任务，处理指定文档并异步提取信息
    
    异步任务将文档送入LLM提取器进行分析并保存结果
    """
    try:
        # 在后台任务中处理文档
        background_tasks.add_task(extraction_service.process_document_by_id, document_id)
        return {"status": "processing", "document_id": document_id, "message": "文档处理已开始，请稍后查询结果"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文档时出错: {str(e)}")


@router.get("/{document_id}", response_model=Dict[str, Any])
def get_extraction(
    document_id: int,
    format: str = None,  # 可选，用于指定响应格式
    extraction_service: InformationExtractionService = Depends(get_extraction_service),
    db: Session = Depends(get_db_session)
):
    """
    获取文档的提取结果
    
    参数:
        document_id: 文档ID
        format: 可选的响应格式，'xlsx' 则返回 Excel 文件，默认返回 JSON 格式
    """
    try:
        # 获取提取结果
        result = extraction_service.get_extraction_result(document_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"文档ID {document_id} 的提取结果不存在")
        
        # 如果指定了xlsx格式，则返回Excel文件
        if format == 'xlsx':
            # 获取文档信息
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise HTTPException(status_code=404, detail=f"文档ID {document_id} 不存在")
            
            # 创建临时目录用于存储Excel文件
            temp_dir = os.path.join(settings.OUTPUT_DIR, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 生成Excel文件名
            file_name = f"{os.path.splitext(document.original_filename)[0]}_extraction_result.xlsx"
            excel_path = os.path.join(temp_dir, file_name)
            
            # 将提取结果保存为Excel
            save_excel(result, excel_path)
            
            # 返回Excel文件供下载
            return FileResponse(
                path=excel_path,
                filename=file_name,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # 默认返回JSON格式的结果
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提取结果时出错: {str(e)}")


@router.put("/{document_id}", response_model=Dict[str, Any])
def update_extraction(
    document_id: int,
    edit_data: ExtractionResultEdit,
    extraction_service: InformationExtractionService = Depends(get_extraction_service),
    db: Session = Depends(get_db_session)
):
    """
    更新（编辑）提取结果
    """
    try:
        edit_service = EditHistoryService(db)
        result = edit_service.edit_extraction_result(
            document_id=document_id,
            edit_data=edit_data.dict(),
            extraction_service=extraction_service
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"编辑提取结果时出错: {str(e)}")


@router.post("/test", response_model=Dict[str, Any])
async def test_extraction(
    file: UploadFile = File(...),
    extraction_service: InformationExtractionService = Depends(get_extraction_service)
):
    """
    测试提取功能
    
    上传一个文档文件，使用LLMExtractor提取信息并返回结果，不保存到数据库
    """
    if not file.filename.endswith(('.doc', '.docx')):
        raise HTTPException(status_code=400, detail="只支持.doc和.docx格式的文件")
    
    # 创建临时文件
    temp_dir = os.path.join(settings.OUTPUT_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    try:
        # 保存上传的文件
        with open(temp_file_path, "wb") as buffer:
            contents = await file.read()
            buffer.write(contents)
        
        # 使用LLMExtractor处理文档
        results = extraction_service.process_document(temp_file_path)
        
        # 格式化结果
        structured_info = extraction_service.format_output(results)
        
        return {
            "status": "success",
            "filename": file.filename,
            "results": structured_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试提取器时出错: {str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/batch", response_model=Dict[str, Any])
async def create_batch_extractions(
    background_tasks: BackgroundTasks,
    limit: int = Query(10, description="最大处理文档数量", ge=1, le=100),
    extraction_service: InformationExtractionService = Depends(get_extraction_service),
    db: Session = Depends(get_db_session)
):
    """
    批量创建提取任务，处理已上传但未处理的文档
    
    参数:
        limit: 最大处理文档数量，默认为10，最大100
    """
    try:
        # 从数据库获取未处理的文档
        unprocessed_documents = db.query(Document).filter(Document.processed == False).order_by(Document.upload_time).limit(limit).all()
        
        if not unprocessed_documents:
            return {
                "status": "info",
                "message": "没有找到未处理的文档",
                "processed_count": 0
            }
        
        # 收集文档ID列表
        document_ids = [doc.id for doc in unprocessed_documents]
        
        # 对每个文档添加后台处理任务
        for doc_id in document_ids:
            background_tasks.add_task(extraction_service.process_document_by_id, doc_id)
        
        return {
            "status": "success",
            "message": f"开始处理 {len(document_ids)} 个文档，处理将在后台进行",
            "processing_document_ids": document_ids,
            "processed_count": len(document_ids)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量处理文档时出错: {str(e)}") 