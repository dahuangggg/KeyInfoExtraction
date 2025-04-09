import json
import requests
from pathlib import Path
import os
from docx import Document
import pandas as pd
from collections import defaultdict
from difflib import SequenceMatcher
import logging
import re
import concurrent.futures
import time
from tqdm import tqdm
import random
import traceback
import sys
from .llm_service import LLMService
from .multi_agent.coordinator_agent import CoordinatorAgent


class LLMExtractor:
    """
    LLM提取器 - 使用大语言模型从文档中提取信息
    
    该提取器负责:
    1. 文档的预处理和文本提取
    2. 调用大语言模型进行信息提取
    3. 结果的后处理和格式化
    """
    
    def __init__(self, llm_service, debug=False):
        """
        初始化LLM提取器
        
        参数:
            llm_service: LLMService实例，用于调用大语言模型
            debug: 是否启用调试模式
        """
        self.llm_service = llm_service
        self.debug = debug
        
        # 配置日志
        self.logger = logging.getLogger("LLMExtractor")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO if not debug else logging.DEBUG)
        
        self.logger.info("初始化LLMExtractor...")
        
        # 初始化协调Agent
        self.coordinator = CoordinatorAgent(llm_service, debug=debug)
        
        self.logger.info("LLMExtractor初始化完成。")
    
    def extract(self, file_path_or_paths, output_dir=None, output_json=True, output_excel=True, batch=True, max_workers=4, batch_by_group=True):
        """
        统一的提取方法，可处理单个文件或多个文件
        
        参数:
            file_path_or_paths: 文档文件路径或文件路径列表
            output_dir: 输出目录，默认为None（输出到各文件所在目录）
            output_json: 是否输出JSON文件
            output_excel: 是否输出Excel文件
            batch: 是否使用批量处理方式
            max_workers: 批量处理时的最大并行工作线程数
            batch_by_group: 批量处理时是否按物理状态组进行批处理
            
        返回:
            单个文件时：提取的结果列表
            多个文件时：文件路径到提取结果的映射字典
        """
        # 判断是单个文件还是多个文件
        is_single_file = isinstance(file_path_or_paths, (str, Path))
        
        # 处理单个文件
        if is_single_file:
            self.logger.info(f"开始处理文档: {file_path_or_paths}")
            return self.coordinator.process_document(
                doc_path=file_path_or_paths, 
                output_dir=output_dir, 
                output_json=output_json, 
                output_excel=output_excel, 
                batch=batch, 
                max_workers=max_workers, 
                batch_by_group=batch_by_group
            )
            
        # 处理多个文件
        else:
            self.logger.info(f"批量处理{len(file_path_or_paths)}个文档文件")
            results = {}
                
            for file_path in tqdm(file_path_or_paths, desc="处理文档"):
                try:
                    file_result = self.coordinator.process_document(
                        doc_path=file_path, 
                        output_dir=output_dir,
                        output_json=output_json,
                        output_excel=output_excel,
                        batch=batch,
                        max_workers=max_workers,
                        batch_by_group=batch_by_group
                    )
                    results[file_path] = file_result
                except Exception as e:
                    self.logger.error(f"处理文档 {file_path} 时出错: {str(e)}")
                    results[file_path] = []
            
            return results
    
    def _call_llm_api(self, prompt, max_retries=3, retry_delay=2):
        """调用LLM API（包含重试机制）
        
        参数:
            prompt: 发送给API的提示词
            max_retries: 最大重试次数
            retry_delay: 初始重试延迟（秒）
            
        返回:
            API响应内容，如果失败则返回空字符串
        """
        # 使用LLMService的call_llm方法
        return self.llm_service.call_llm(prompt, max_retries, retry_delay)
    
    def _extract_json_from_response(self, response, is_array=False):
        """从LLM响应中提取JSON部分
        
        参数:
            response: LLM的响应文本
            is_array: 是否需要提取JSON数组（默认为False，提取单个JSON对象）
            
        返回:
            提取出的JSON字符串，如果无法提取则返回空字符串
        """
        # 使用LLMService的extract_json_from_response方法
        return self.llm_service.extract_json_from_response(response, is_array)
    
    def extract_from_text(self, text, output_dir=None, output_json=False, output_excel=False, batch=True, max_workers=4, batch_by_group=True, filename='text_extraction'):
        """从文本内容中提取信息（无需文档文件）
        
        参数:
            text: 待分析的文本内容
            output_dir: 输出目录，默认为None（不输出文件）
            output_json: 是否输出JSON文件
            output_excel: 是否输出Excel文件
            batch: 是否使用批量处理方式
            max_workers: 批量处理时的最大并行工作线程数
            batch_by_group: 批量处理时是否按物理状态组进行批处理
            filename: 输出文件的基础名称（不含扩展名）
            
        返回:
            提取的结果列表
        """
        self.logger.info(f"从文本内容中提取信息，文本长度: {len(text)}字符")
        
        return self.coordinator.process_document(
            doc_text=text, 
            output_dir=output_dir, 
            output_json=output_json, 
            output_excel=output_excel, 
            batch=batch, 
            max_workers=max_workers, 
            batch_by_group=batch_by_group
        )