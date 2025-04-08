"""
Multi-Agent架构中的prompt模板包

该包包含所有用于提取信息的prompt模板，按功能分类：
- identification.py: 用于识别物理状态组和物理状态的prompt
- extraction.py: 用于提取具体物理状态值的prompt
"""

from .identification import IDENTIFICATION_PROMPT
from .extraction import EXTRACTION_GUIDELINES, EXTRACTION_SINGLE_PROMPT, EXTRACTION_BATCH_PROMPT

__all__ = ['IDENTIFICATION_PROMPT', 'EXTRACTION_GUIDELINES', 'EXTRACTION_SINGLE_PROMPT', 'EXTRACTION_BATCH_PROMPT']