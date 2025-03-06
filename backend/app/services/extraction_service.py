import os
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.extraction import ExtractionResult, PhysicalStateGroup, PhysicalStateItem
from app.utils import save_json, save_excel, filter_empty_values, DocProcessor
from app.extractors import LLMExtractor
from app.extractors.rule_extractor import InformationExtractor

class InformationExtractionService:
    """信息提取系统服务"""
    
    def __init__(self, db: Session = None, use_custom_models=None, ner_model_path=None, relation_model_path=None):
        """
        初始化信息提取系统
        
        参数:
            db: 数据库会话
            use_custom_models: 是否使用自定义训练的模型
            ner_model_path: NER模型路径
            relation_model_path: 关系抽取模型路径
        """
        self.db = db
        self.doc_processor = DocProcessor()
        
        # 使用配置文件中的设置，如果未提供参数
        self.use_custom_models = use_custom_models if use_custom_models is not None else settings.USE_CUSTOM_MODELS
        self.ner_model_path = ner_model_path or settings.NER_MODEL_PATH
        self.relation_model_path = relation_model_path or settings.RELATION_MODEL_PATH
        
        # 根据配置选择使用的提取器
        if self.use_custom_models:
            print(f"使用自定义训练的模型: NER={self.ner_model_path}, Relation={self.relation_model_path}")
            self.rule_extractor = InformationExtractor(
                ner_model_path=self.ner_model_path,
                relation_model_path=self.relation_model_path,
                use_models=True
            )
            self.extractor = self.rule_extractor
        else:
            print("使用LLM提取器")
            self.llm_extractor = LLMExtractor()
            self.extractor = self.llm_extractor
        
    def process_document(self, file_path):
        """处理单个文档"""
        # 解析文档
        text = self.doc_processor.parse_docx(file_path)
        
        # 分割章节
        sections = self.doc_processor.split_into_sections(text)
        
        # 提取信息
        results = {}
        for section_title, section_text in sections.items():
            print(f"处理章节: {section_title}")
            # 使用选定的提取器提取信息
            section_info = self.extractor.extract_info(section_text, section_title)
            results[section_title] = section_info
        
        return results
    
    def format_output(self, results):
        """格式化输出结果"""
        # 初始化结构化信息
        structured_info = {
            "元器件物理状态分析": []
        }
        
        # 遍历所有章节
        for section_title, section_info in results.items():
            # 跳过附图和附表章节
            if "附图" in section_title or "附表" in section_title:
                print(f"跳过章节: {section_title}")
                continue
                
            # 检查是否存在物理状态组信息
            if "物理状态组" in section_info:
                # 将物理状态组信息添加到结构化信息中
                physical_state_group = {
                    "物理状态组": section_title,
                    "物理状态项": []
                }
                
                for state in section_info["物理状态组"]:
                    physical_state_item = {
                        "物理状态名称": state.get("物理状态名称", ""),
                        "典型物理状态值": state.get("典型物理状态值", ""),
                        "禁限用信息": state.get("禁限用信息", "无"),
                        "测试评语": state.get("测试评语", "")
                    }
                    physical_state_group["物理状态项"].append(physical_state_item)
                
                structured_info["元器件物理状态分析"].append(physical_state_group)
            else:
                # 尝试处理旧格式
                print(f"警告: 章节 {section_title} 的数据格式不符合预期，尝试转换...")
                
                # 尝试从旧格式转换
                physical_state_items = []
                
                # 遍历章节信息中的所有键
                for key, value in section_info.items():
                    # 跳过非字典类型的值
                    if not isinstance(value, dict):
                        continue
                    
                    # 构建物理状态
                    physical_state_item = {
                        "物理状态名称": key,
                        "典型物理状态值": value.get("值", "文中未提及"),
                        "禁限用信息": value.get("禁限用信息", "无"),
                        "测试评语": value.get("测试评语", "文中未提及")
                    }
                    
                    physical_state_items.append(physical_state_item)
                
                # 添加到结构化信息
                if physical_state_items:
                    physical_state_group = {
                        "物理状态组": section_title,
                        "物理状态项": physical_state_items
                    }
                    structured_info["元器件物理状态分析"].append(physical_state_group)
                else:
                    print(f"警告: 无法从章节 {section_title} 提取物理状态信息")
        
        return structured_info
    
    def process_document_by_id(self, document_id: int) -> Dict[str, Any]:
        """
        根据文档ID处理文档并保存结果到数据库
        """
        if not self.db:
            raise ValueError("数据库会话未初始化")
            
        # 获取文档
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"找不到ID为{document_id}的文档")
            
        # 检查文档是否已处理
        if document.processed:
            # 获取已有的提取结果
            extraction_result = self.db.query(ExtractionResult).filter(
                ExtractionResult.document_id == document_id
            ).first()
            
            if extraction_result:
                return json.loads(extraction_result.result_json)
            
        # 处理文档
        start_time = time.time()
        results = self.process_document(document.file_path)
        structured_info = self.format_output(results)
        processing_time = time.time() - start_time
        
        # 保存结果到数据库
        self._save_extraction_result(document_id, structured_info, processing_time)
        
        # 更新文档处理状态
        document.processed = True
        document.processing_time = processing_time
        self.db.commit()
        
        return structured_info
    
    def _save_extraction_result(self, document_id: int, structured_info: Dict[str, Any], processing_time: float) -> ExtractionResult:
        """
        保存提取结果到数据库
        """
        # 创建提取结果记录
        extraction_result = ExtractionResult(
            document_id=document_id,
            extraction_time=datetime.now(),
            result_json=json.dumps(structured_info, ensure_ascii=False),
            is_edited=False
        )
        
        self.db.add(extraction_result)
        self.db.flush()  # 获取ID但不提交事务
        
        # 添加物理状态组和物理状态项
        for group_data in structured_info.get("元器件物理状态分析", []):
            group = PhysicalStateGroup(
                extraction_result_id=extraction_result.id,
                group_name=group_data.get("物理状态组", "")
            )
            
            self.db.add(group)
            self.db.flush()  # 获取ID但不提交事务
            
            # 添加物理状态项
            for item_data in group_data.get("物理状态项", []):
                item = PhysicalStateItem(
                    physical_state_group_id=group.id,
                    state_name=item_data.get("物理状态名称", ""),
                    state_value=item_data.get("典型物理状态值", ""),
                    prohibition_info=item_data.get("禁限用信息", "无"),
                    test_comment=item_data.get("测试评语", "")
                )
                
                self.db.add(item)
        
        # 提交事务
        self.db.commit()
        self.db.refresh(extraction_result)
        
        return extraction_result
    
    def get_extraction_result(self, document_id: int) -> Optional[Dict[str, Any]]:
        """
        获取文档的提取结果
        """
        if not self.db:
            raise ValueError("数据库会话未初始化")
            
        extraction_result = self.db.query(ExtractionResult).filter(
            ExtractionResult.document_id == document_id
        ).first()
        
        if extraction_result:
            return json.loads(extraction_result.result_json)
        
        return None
    
    def batch_process(self, directory_path, output_dir=None, output_format="json"):
        """批量处理目录中的文档"""
        # 使用配置中的输出目录（如果未提供）
        output_dir = output_dir or settings.OUTPUT_DIR
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取目录中的所有docx文件
        docx_files = []
        for file in os.listdir(directory_path):
            if file.endswith(".docx") and not file.startswith("~$"):
                docx_files.append(os.path.join(directory_path, file))
        
        print(f"找到 {len(docx_files)} 个docx文件")
        
        # 处理每个文件
        results = []
        for file_path in docx_files:
            file_name = os.path.basename(file_path)
            print(f"处理文件: {file_name}")
            
            try:
                # 处理文档
                doc_results = self.process_document(file_path)
                
                # 格式化输出
                structured_info = self.format_output(doc_results)
                
                # 保存结果
                base_output_file = os.path.join(output_dir, os.path.splitext(file_name)[0])
                
                # 根据指定格式保存
                if output_format in ["json", "both"]:
                    json_output_file = base_output_file + ".json"
                    save_json(structured_info, json_output_file)
                
                if output_format in ["excel", "both"]:
                    excel_output_file = base_output_file + ".xlsx"
                    save_excel(structured_info, excel_output_file)
                
                # 添加到结果列表
                results.append({
                    "file_name": file_name,
                    "output_files": {
                        "json": json_output_file if output_format in ["json", "both"] else None,
                        "excel": excel_output_file if output_format in ["excel", "both"] else None
                    },
                    "structured_info": structured_info
                })
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
                results.append({
                    "file_name": file_name,
                    "error": str(e)
                })
        
        print("批处理完成")
        return results
    
    def process_text(self, text, section_type="通用"):
        """处理文本内容"""
        # 直接提取信息
        section_info = self.extractor.extract_info(text, section_type)
        
        # 格式化输出
        results = {section_type: section_info}
        structured_info = self.format_output(results)
        
        return structured_info 