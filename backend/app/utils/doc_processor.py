import os
import re
import jieba
import subprocess
import tempfile
from typing import Dict, List, Any

class DocProcessor:
    """文档处理类，负责解析和预处理文档"""
    
    def __init__(self, stopwords_path="../../data/stopwords.txt"):
        # 加载停用词
        self.stopwords = set()
        if os.path.exists(stopwords_path):
            with open(stopwords_path, 'r', encoding='utf-8') as f:
                for line in f:
                    self.stopwords.add(line.strip())
        
        # 添加专业术语到jieba分词词典
        self.add_domain_terms()
    
    def add_domain_terms(self):
        """向jieba添加领域专用词汇"""
        domain_terms = [
            "CQFP48", "Au/Sn", "Fe/Ni", "CuAg", "键合丝", "玻璃钝化层", 
            "化学机械抛光", "CMP", "金属化布线", "芯片粘接"
        ]
        for term in domain_terms:
            jieba.add_word(term)
    
    def parse_docx(self, file_path):
        """解析docx文件内容"""
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return ""
            
        # 检查文件扩展名
        if file_path.endswith('.docx'):
            try:
                import docx
                doc = docx.Document(file_path)
                content = "\n".join([para.text for para in doc.paragraphs])
                return content
            except ImportError:
                print("请安装python-docx库: pip install python-docx")
                return ""
            except Exception as e:
                print(f"解析docx文件出错: {e}")
                return ""
        # 如果是doc文件
        elif file_path.endswith('.doc'):
            # 由于doc文件处理比较复杂，这里简化处理
            # 建议用户先将doc转换为docx格式
            print(f"请先将doc文件 '{file_path}' 转换为docx格式后再处理")
            
            # 尝试读取同名的docx文件
            docx_path = file_path.replace('.doc', '.docx')
            if os.path.exists(docx_path):
                print(f"找到同名docx文件，尝试处理: {docx_path}")
                return self.parse_docx(docx_path)
            
            # 如果没有同名docx文件，返回空字符串
            return ""
        # 如果是纯文本文件
        elif file_path.endswith('.txt'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    return content
                except Exception as e:
                    print(f"解析文本文件出错: {e}")
                    return ""
        else:
            print(f"不支持的文件格式: {file_path}")
            return ""
    
    def segment_text(self, text):
        """中文分词处理"""
        words = jieba.cut(text)
        # 过滤停用词
        words = [w for w in words if w not in self.stopwords and w.strip()]
        return words
    
    def split_into_sections(self, text):
        """将文档分割为不同章节"""
        # 使用正则表达式匹配章节标题
        sections = {}
        # 示例正则，实际应根据文档结构调整
        section_pattern = r'([一二三四五六七八九十]+、[\S]+)\n'
        subsection_pattern = r'([1-9][0-9]*[、）\)].+)\n'
        
        # 查找所有主章节
        main_sections = re.finditer(section_pattern, text)
        prev_pos = 0
        prev_section = None
        
        for match in main_sections:
            section_title = match.group(1)
            start_pos = match.start()
            
            # 保存上一个章节内容
            if prev_section:
                sections[prev_section] = text[prev_pos:start_pos]
            
            prev_section = section_title
            prev_pos = match.end()
        
        # 保存最后一个章节
        if prev_section:
            sections[prev_section] = text[prev_pos:]
            
        return sections 