from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseExtractor(ABC):
    """基础信息提取器抽象类"""
    
    @abstractmethod
    def extract_info(self, text, section_type):
        """
        从文本中提取信息
        
        参数:
            text: 要处理的文本
            section_type: 章节类型
            
        返回:
            提取的信息
        """
        pass 