import json
import logging
import os
from docx import Document
import pandas as pd

from .extraction_agent import ExtractionAgent
from .identification_agent import IdentificationAgent
from .validation_agent import ValidationAgent


class CoordinatorAgent:
    """
    协调Agent - 负责管理整个提取过程

    该Agent负责:
    1. 组织文档处理流程
    2. 识别物理状态组和物理状态
    3. 提取具体的物理状态值
    4. 验证和优化提取结果
    5. 与知识库交互
    """

    def __init__(self, llm_service, debug=False):
        """
        初始化协调Agent

        参数:
            llm_service: LLMService实例，用于调用大语言模型
            debug: 是否启用调试模式
        """
        self.llm_service = llm_service
        self.debug = debug

        # 配置日志
        self.logger = logging.getLogger("CoordinatorAgent")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO if not debug else logging.DEBUG)

        self.logger.info("初始化CoordinatorAgent...")

        # 初始化识别Agent、提取Agent和验证Agent
        self.identification_agent = IdentificationAgent(llm_service, debug=debug)
        self.extraction_agent = ExtractionAgent(llm_service, debug=debug)
        self.validation_agent = ValidationAgent(llm_service, debug=debug)

        self.logger.info("CoordinatorAgent初始化完成。")

    def process_document(self, doc_path=None, doc_text=None, output_dir=None, output_json=True, output_excel=True,
                         batch=True, max_workers=4, batch_by_group=True):
        """
        处理文档，提取物理状态信息

        参数:
            doc_path: 文档路径（与doc_text二选一）
            doc_text: 文档文本内容（与doc_path二选一）
            output_dir: 输出目录路径（可选）
            output_json: 是否输出JSON文件
            output_excel: 是否输出Excel文件
            batch: 是否使用批量处理模式
            max_workers: 批量处理的最大线程数
            batch_by_group: 批量处理时是否按物理状态组分组

        返回:
            提取的结果列表
        """
        # 获取文档内容
        if doc_path:
            self.logger.info(f"正在读取文档: {doc_path}")
            try:
                doc = Document(doc_path)
                text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])

                # 检查文档是否为空
                if not text.strip():
                    self.logger.error(f"文档内容为空: {doc_path}")
                    return []

                # 显示文档信息
                text_length = len(text)
                self.logger.info(f"文档长度: {text_length} 字符")

            except Exception as e:
                self.logger.error(f"读取文档失败: {str(e)}")
                return []
        elif doc_text:
            text = doc_text
            text_length = len(text)
            self.logger.info(f"使用提供的文本内容，长度: {text_length} 字符")
        else:
            self.logger.error("必须提供doc_path或doc_text参数")
            return []

        # 阶段1: 识别物理状态组和物理状态 - 使用识别Agent
        self.logger.info("阶段1: 正在识别文档中的物理状态组和物理状态...")
        identified_states = self.identification_agent.identify_groups_and_states(text)

        # 阶段2: 提取具体值 - 使用提取Agent
        self.logger.info("阶段2: 正在提取具体的物理状态值...")
        extraction_results = self.extraction_agent.extract_specific_values(
            text,
            identified_states,
            parallel=True,
            max_workers=max_workers,
            batch=batch,
            batch_by_group=batch_by_group
        )

        # 阶段3: 验证和优化结果 - 使用验证Agent
        self.logger.info("阶段3: 正在验证和优化提取结果...")
        validated_results = self.validation_agent.validate_extraction_results(text, extraction_results)

        # 结果保存
        if doc_path and (output_json or output_excel) and validated_results:
            # 确定输出路径
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                base_name = os.path.basename(doc_path)
                name_without_ext = os.path.splitext(base_name)[0]
                output_base = os.path.join(output_dir, name_without_ext)
            else:
                # 默认输出到文档所在目录
                doc_dir = os.path.dirname(doc_path)
                name_without_ext = os.path.splitext(os.path.basename(doc_path))[0]
                output_base = os.path.join(doc_dir, name_without_ext)

            # 输出JSON文件
            if output_json:
                json_path = f"{output_base}_extraction.json"
                try:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(validated_results, f, ensure_ascii=False, indent=2)
                    self.logger.info(f"已保存JSON结果到: {json_path}")
                except Exception as e:
                    self.logger.error(f"保存JSON结果失败: {str(e)}")

            # 输出Excel文件
            if output_excel:
                excel_path = f"{output_base}_extraction.xlsx"
                try:
                    # 将结果转换为DataFrame
                    df = pd.DataFrame(validated_results)

                    # 保存为Excel
                    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='提取结果')

                    self.logger.info(f"已保存Excel结果到: {excel_path}")
                except Exception as e:
                    self.logger.error(f"保存Excel结果失败: {str(e)}")

        return validated_results