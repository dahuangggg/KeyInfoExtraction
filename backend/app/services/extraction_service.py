import os
import time
import json
import subprocess
import tempfile
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.extraction import ExtractionResult, PhysicalStateGroup, PhysicalStateItem
from app.utils import save_json, save_excel, filter_empty_values, DocProcessor
from app.extractors import LLMExtractor

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("警告: python-docx 未安装, 文档预处理功能将受限")

class InformationExtractionService:
    """信息提取系统服务"""
    
    def __init__(self, db: Session = None, extractor: LLMExtractor = None):
        """
        初始化信息提取系统
        
        参数:
            db: 数据库会话
            extractor: LLM提取器实例
        """
        self.db = db
        self.doc_processor = DocProcessor()
        
        # 使用外部提供的LLM提取器
        if extractor:
            self.extractor = extractor
        else:
            # 如果未提供提取器，抛出错误
            raise ValueError("必须提供LLMExtractor实例")
        
    def read_docx(self, file_path):
        """
        读取docx文件内容
        
        参数:
            file_path: docx文件路径
        
        返回:
            文档文本内容
        """
        if not HAS_DOCX:
            raise ImportError("需要安装python-docx: pip install python-docx")
            
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)

    def clean_text(self, text):
        """
        清洗文本，去除多余空格和特殊字符，但保留重要的标点和数值信息
        
        参数:
            text: 原始文本
        
        返回:
            清洗后的文本
        """
        # 去除多余空格，但保留单个空格
        text = re.sub(r'\s+', ' ', text)
        
        # 去除特殊字符，但保留需要的标点和数值相关字符
        # 保留中英文标点、数字、字母、单位符号
        text = re.sub(r'[^\w\s,.，。、；：""（）()μ%℃@\-\+\.g]', '', text)
        
        return text
    
    def convert_doc_to_docx(self, doc_path, output_dir=None):
        """
        尝试将doc文件转换为docx格式
        
        参数:
            doc_path: doc文件路径
            output_dir: 输出目录，默认为None（创建临时目录）
        
        返回:
            转换后的docx文件路径，如果转换失败则返回None
        """
        # 如果未指定输出目录，创建临时目录
        if output_dir is None:
            output_dir = os.path.join(settings.OUTPUT_DIR, "temp")
            os.makedirs(output_dir, exist_ok=True)
        
        # 构建输出文件路径
        file_name = os.path.basename(doc_path)
        docx_name = os.path.splitext(file_name)[0] + '.docx'
        output_path = os.path.join(output_dir, docx_name)
        
        # 检查是否存在LibreOffice
        libreoffice_paths = [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS
            "soffice",  # 如果在PATH中
            "libreoffice",  # 某些Linux发行版
            r"C:\Program Files\LibreOffice\program\soffice.exe",  # Windows
        ]
        
        libreoffice_path = None
        for path in libreoffice_paths:
            try:
                if os.path.exists(path) or (path in ["soffice", "libreoffice"] and subprocess.call(["which", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0):
                    libreoffice_path = path
                    break
            except:
                continue
        
        if not libreoffice_path:
            print(f"警告: 未找到LibreOffice，将尝试直接读取doc文件")
            return None
        
        try:
            # 执行转换命令
            cmd = [libreoffice_path, '--headless', '--convert-to', 'docx', '--outdir', output_dir, doc_path]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"转换失败: {stderr.decode('utf-8', errors='ignore')}")
                return None
            
            # 检查转换后的文件是否存在
            if os.path.exists(output_path):
                print(f"成功转换: {doc_path} -> {output_path}")
                return output_path
            else:
                print(f"转换后的文件不存在: {output_path}")
                return None
        
        except Exception as e:
            print(f"转换过程中出错: {e}")
            return None
    
    def preprocess_document(self, file_path):
        """
        预处理文档，确保它能被正确读取
        
        参数:
            file_path: 文档文件路径
            
        返回:
            文档文本内容
        """
        # 检查文件扩展名
        is_doc = file_path.lower().endswith('.doc')
        is_docx = file_path.lower().endswith('.docx')
        
        if not (is_doc or is_docx):
            raise ValueError(f"不支持的文件格式: {file_path}")
        
        # 如果是doc文件，尝试转换为docx
        if is_doc:
            print(f"尝试转换doc文件: {file_path}")
            docx_path = self.convert_doc_to_docx(file_path)
            
            # 如果转换成功，使用转换后的docx文件
            if docx_path:
                try:
                    text_content = self.read_docx(docx_path)
                    # 清理临时文件
                    try:
                        os.remove(docx_path)
                    except:
                        pass
                    return text_content
                except Exception as e:
                    print(f"读取转换后的docx文件失败: {e}")
                    # 继续尝试其他方法
            
            # 如果转换失败，尝试使用antiword或其他工具
            print("尝试使用其他方法提取doc文件内容")
            try:
                # 创建临时文本文件
                temp_dir = os.path.join(settings.OUTPUT_DIR, "temp")
                os.makedirs(temp_dir, exist_ok=True)
                temp_txt = os.path.join(temp_dir, f"{os.path.splitext(os.path.basename(file_path))[0]}.txt")
                
                # 尝试使用antiword
                try:
                    cmd = ['antiword', file_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        with open(temp_txt, 'w', encoding='utf-8') as f:
                            f.write(result.stdout)
                        with open(temp_txt, 'r', encoding='utf-8') as f:
                            return f.read()
                except:
                    pass
                
                # 尝试使用textract
                try:
                    import textract
                    text = textract.process(file_path).decode('utf-8')
                    with open(temp_txt, 'w', encoding='utf-8') as f:
                        f.write(text)
                    return text
                except:
                    pass
                
                # 如果都失败了，返回错误
                raise ValueError(f"无法读取doc文件: {file_path}，请确保文件格式正确或安装相关工具（LibreOffice、antiword或textract）")
                
            except Exception as e:
                raise ValueError(f"提取doc文件内容失败: {str(e)}")
        
        # 如果是docx文件，直接读取
        if is_docx:
            try:
                return self.read_docx(file_path)
            except Exception as e:
                raise ValueError(f"读取docx文件失败: {str(e)}")
        
    def process_document(self, file_path):
        """处理单个文档"""
        try:
            # 尝试预处理文档
            text_content = None
            try:
                text_content = self.preprocess_document(file_path)
                print(f"成功提取文档内容，长度: {len(text_content)} 字符")
                
                # 可以选择将文本内容保存为临时文件，便于调试
                temp_dir = os.path.join(settings.OUTPUT_DIR, "temp")
                os.makedirs(temp_dir, exist_ok=True)
                temp_txt = os.path.join(temp_dir, f"{os.path.splitext(os.path.basename(file_path))[0]}_extracted.txt")
                with open(temp_txt, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                print("使用提取到的文本内容进行分析")
            except Exception as e:
                print(f"预处理文档失败: {e}")
                print("尝试直接使用原始文档...")
            
            # 根据是否成功提取文本决定处理方式
            if text_content:
                # 使用文本内容进行提取
                results = self.extractor.extract_from_text(
                    text=text_content,
                    output_dir=settings.OUTPUT_DIR,
                    output_json=True,
                    output_excel=True,
                    filename=os.path.splitext(os.path.basename(file_path))[0]
                )
            else:
                # 直接使用原始文件
                results = self.extractor.extract(
                    file_path_or_paths=file_path,
                    output_dir=settings.OUTPUT_DIR,
                    output_json=True,
                    output_excel=True
                )
            return results
        except Exception as e:
            print(f"处理文档时出错: {e}")
            return None
    
    def format_output(self, results):
        """格式化输出结果"""
        # 初始化结构化信息
        structured_info = {
            "元器件物理状态分析": []
        }
        
        # 检查结果是否为空
        if not results:
            return structured_info
            
        # 处理LLMExtractor返回的结果，可能是列表或字典
        if isinstance(results, list):
            # 当results是列表时（LLMExtractor的新版结果格式）
            # 按物理状态组分组
            grouped_results = {}
            for item in results:
                group_name = item.get("物理状态组", "未知组")
                state_name = item.get("物理状态", "未知状态")
                
                if group_name not in grouped_results:
                    grouped_results[group_name] = {}
                
                grouped_results[group_name][state_name] = {
                    "值": item.get("物理状态值", ""),
                    "禁限用信息": item.get("风险评价", "无"),
                    "测试评语": item.get("测试评语", ""),
                    "试验项目": item.get("试验项目", "")
                }
            
            # 继续处理分组后的结果
            for group_name, states in grouped_results.items():
                group_data = {
                    "物理状态组": group_name,
                    "物理状态项": []
                }
                
                for state_name, state_info in states.items():
                    state_data = {
                        "物理状态名称": state_name,
                        "典型物理状态值": state_info.get("值", ""),
                        "禁限用信息": state_info.get("禁限用信息", "无"),
                        "测试评语": state_info.get("测试评语", ""),
                        "试验项目": state_info.get("试验项目", "")
                    }
                    group_data["物理状态项"].append(state_data)
                
                structured_info["元器件物理状态分析"].append(group_data)
                
        elif isinstance(results, dict):
            # 当results是字典时（兼容可能的旧版格式）
            for group_name, states in results.items():
                group_data = {
                    "物理状态组": group_name,
                    "物理状态项": []
                }
                
                for state_name, state_info in states.items():
                    state_data = {
                        "物理状态名称": state_name,
                        "典型物理状态值": state_info.get("值", ""),
                        "禁限用信息": state_info.get("禁限用信息", "无"),
                        "测试评语": state_info.get("测试评语", ""),
                        "试验项目": state_info.get("试验项目", "")
                    }
                    group_data["物理状态项"].append(state_data)
                
                structured_info["元器件物理状态分析"].append(group_data)
                
        return structured_info
    
    def process_document_by_id(self, document_id: int) -> Dict[str, Any]:
        """
        处理指定ID的文档
        
        参数:
            document_id: 文档ID
        
        返回:
            提取结果的结构化信息
        """
        if not self.db:
            raise ValueError("数据库会话未初始化")
        
        # 查询文档
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"找不到ID为 {document_id} 的文档")
        
        # 确保文件存在
        file_path = document.file_path
        if not os.path.exists(file_path):
            raise ValueError(f"文件不存在: {file_path}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 处理文档
        results = self.process_document(file_path)
        
        # 格式化输出
        structured_info = self.format_output(results)
        
        # 计算处理时间
        processing_time = time.time() - start_time
        
        # 保存结果
        extraction_result = self._save_extraction_result(document_id, structured_info, processing_time)
        
        # 更新文档处理状态
        from app.services.document_service import DocumentService
        document_service = DocumentService(self.db)
        document_service.mark_document_as_processed(document_id, processing_time)
        
        return structured_info
    
    def _save_extraction_result(self, document_id: int, structured_info: Dict[str, Any], processing_time: float) -> ExtractionResult:
        """
        保存提取结果到数据库
        
        参数:
            document_id: 文档ID
            structured_info: 结构化信息
            processing_time: 处理时间（秒）
        
        返回:
            创建的ExtractionResult实例
        """
        if not self.db:
            raise ValueError("数据库会话未初始化")
        
        # 查询是否存在之前的结果
        existing_result = self.db.query(ExtractionResult).filter(
            ExtractionResult.document_id == document_id
        ).first()
        
        # 如果存在之前的结果，删除它
        if existing_result:
            self.db.delete(existing_result)
            self.db.commit()
        
        # 创建新的提取结果
        extraction_result = ExtractionResult(
            document_id=document_id,
            result_json=json.dumps(structured_info, ensure_ascii=False),
            is_edited=False
        )
        
        self.db.add(extraction_result)
        self.db.commit()
        self.db.refresh(extraction_result)
        
        # 创建物理状态组和物理状态项记录
        for group_info in structured_info.get("元器件物理状态分析", []):
            group = PhysicalStateGroup(
                extraction_result_id=extraction_result.id,
                group_name=group_info.get("物理状态组", "未知组")
            )
            
            self.db.add(group)
            self.db.commit()
            self.db.refresh(group)
            
            # 创建物理状态项
            for item_info in group_info.get("物理状态项", []):
                state_value = item_info.get("典型物理状态值", "")
                if isinstance(state_value, dict):
                    state_value = json.dumps(state_value, ensure_ascii=False)
                
                item = PhysicalStateItem(
                    physical_state_group_id=group.id,
                    state_name=item_info.get("物理状态名称", ""),
                    state_value=state_value,
                    prohibition_info=item_info.get("禁限用信息", ""),
                    test_comment=item_info.get("测试评语", ""),
                    test_project=item_info.get("试验项目", "")
                )
                
                self.db.add(item)
        
        self.db.commit()
        
        return extraction_result
    
    def get_extraction_result(self, document_id: int) -> Optional[Dict[str, Any]]:
        """
        获取文档的提取结果
        
        参数:
            document_id: 文档ID
        
        返回:
            提取结果的结构化信息，如果不存在则返回None
        """
        if not self.db:
            raise ValueError("数据库会话未初始化")
        
        # 查询提取结果
        extraction_result = self.db.query(ExtractionResult).filter(
            ExtractionResult.document_id == document_id
        ).first()
        
        if not extraction_result:
            return None
        
        # 返回JSON结果
        return json.loads(extraction_result.result_json)
    
    def batch_process(self, directory_path, output_dir=None, output_format="json"):
        """
        批量处理文档目录
        
        参数:
            directory_path: 文档目录路径
            output_dir: 输出目录路径 (默认: 与directory_path相同)
            output_format: 输出格式 (json, excel, both)
            
        返回:
            处理结果字典
        """
        # 验证目录
        if not os.path.exists(directory_path):
            raise ValueError(f"目录不存在: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise ValueError(f"路径不是目录: {directory_path}")
        
        # 确定输出目录
        if not output_dir:
            output_dir = directory_path
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # 获取目录中的所有.doc和.docx文件
        docx_files = []
        for file in os.listdir(directory_path):
            if file.endswith(('.doc', '.docx')):
                docx_files.append(os.path.join(directory_path, file))
        
        if not docx_files:
            return {"status": "warning", "message": "目录中没有.doc或.docx文件"}
        
        # 处理每个文件
        results = {}
        
        for file_path in docx_files:
            try:
                print(f"处理文件: {os.path.basename(file_path)}")
                
                # 使用LLMExtractor处理文档
                extracted_results = self.extractor.extract(
                    file_path_or_paths=file_path,
                    output_dir=output_dir,
                    output_json=output_format in ["json", "both"],
                    output_excel=output_format in ["excel", "both"]
                )
                
                # 格式化输出
                structured_info = self.format_output(extracted_results)
                
                # 保存结果文件
                base_output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(file_path))[0])
                
                # 根据指定格式保存
                json_output_file = None
                excel_output_file = None
                
                if output_format in ["json", "both"]:
                    json_output_file = base_output_file + ".json"
                    save_json(structured_info, json_output_file)
                
                if output_format in ["excel", "both"]:
                    excel_output_file = base_output_file + ".xlsx"
                    save_excel(structured_info, excel_output_file)
                
                # 记录结果
                results[os.path.basename(file_path)] = {
                    "status": "success",
                    "json": json_output_file if output_format in ["json", "both"] else None,
                    "excel": excel_output_file if output_format in ["excel", "both"] else None
                }
                
            except Exception as e:
                print(f"处理 {os.path.basename(file_path)} 时出错: {e}")
                results[os.path.basename(file_path)] = {"status": "error", "message": str(e)}
        
        return results 