from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseExtractor(ABC):
    """提取器基类，定义提取器的通用接口"""
    
    @abstractmethod
    def extract_info(self, text: str, section_type: str) -> Dict[str, Any]:
        """
        从文本中提取信息
        
        Args:
            text: 待提取的文本
            section_type: 章节类型
            
        Returns:
            包含提取信息的字典
        """
        pass 