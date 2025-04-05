import os
import re
import json
from tqdm import tqdm
import docx
import pandas as pd


def read_docx(file_path):
    """
    读取docx文件内容
    
    Args:
        file_path: docx文件路径
    
    Returns:
        文档文本内容
    """
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def load_documents(doc_dir):
    """
    加载目录中的所有docx文档
    
    Args:
        doc_dir: 文档目录
    
    Returns:
        文档列表，每个文档为一个字典，包含file_name和text字段
    """
    documents = []
    for file in os.listdir(doc_dir):
        if file.endswith('.docx'):
            try:
                doc_text = read_docx(os.path.join(doc_dir, file))
                documents.append({
                    'file_name': file,
                    'text': doc_text
                })
            except Exception as e:
                print(f"Error reading {file}: {e}")
    return documents

def clean_text(text):
    """
    清洗文本，去除多余空格和特殊字符，但保留重要的标点和数值信息
    
    Args:
        text: 原始文本
    
    Returns:
        清洗后的文本
    """
    # 去除多余空格，但保留单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 去除特殊字符，但保留需要的标点和数值相关字符
    # 保留中英文标点、数字、字母、单位符号
    text = re.sub(r'[^\w\s,.，。、；：""（）()μ%℃@\-\+\.g]', '', text)
    
    return text

def build_knowledge_base(json_path):
    """
    从JSON文件构建知识库
    
    Args:
        json_path: 知识库JSON文件路径
    
    Returns:
        知识库字典，包含实体集合和关系映射
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    knowledge_base = {
        'PhyGroup': set(),  # 物理状态组
        'PhyState': set(),  # 物理状态
        'TestItem': set(),  # 试验项目
        'PhyStateValue': set(),  # 物理状态值
        'RiskEval': set(),  # 风险评价
        
        # 关系映射
        'PhyGroup2PhyState': {},  # 物理状态组 -> 物理状态
        'PhyState2Value': {},     # 物理状态 -> 物理状态值
        'PhyState2RiskEval': {}   # 物理状态 -> 风险评价
    }
    
    # 填充知识库
    for item in data:
        phy_group = item.get('物理状态组', '')
        phy_state = item.get('物理状态', '')
        test_item = item.get('试验项目', '')
        phy_value = item.get('物理状态值', '')
        risk_eval = item.get('风险评价', '')
        
        if phy_group: knowledge_base['PhyGroup'].add(phy_group)
        if phy_state: knowledge_base['PhyState'].add(phy_state)
        if test_item: 
            # 处理试验项目中的多个项目（逗号分隔）
            for t in re.split(r'[,，、]', test_item):
                t = t.strip()
                if t: knowledge_base['TestItem'].add(t)
        if phy_value: knowledge_base['PhyStateValue'].add(phy_value)
        if risk_eval: knowledge_base['RiskEval'].add(risk_eval)
        
        # 建立关系映射
        if phy_group and phy_state:
            if phy_group not in knowledge_base['PhyGroup2PhyState']:
                knowledge_base['PhyGroup2PhyState'][phy_group] = set()
            knowledge_base['PhyGroup2PhyState'][phy_group].add(phy_state)
        
        if phy_state and phy_value:
            if phy_state not in knowledge_base['PhyState2Value']:
                knowledge_base['PhyState2Value'][phy_state] = set()
            knowledge_base['PhyState2Value'][phy_state].add(phy_value)
        
        if phy_state and risk_eval:
            if phy_state not in knowledge_base['PhyState2RiskEval']:
                knowledge_base['PhyState2RiskEval'][phy_state] = set()
            knowledge_base['PhyState2RiskEval'][phy_state].add(risk_eval)
    
    # 将集合转换为列表，方便序列化
    for key in knowledge_base:
        if isinstance(knowledge_base[key], set):
            knowledge_base[key] = list(knowledge_base[key])
        elif isinstance(knowledge_base[key], dict):
            for sub_key in knowledge_base[key]:
                if isinstance(knowledge_base[key][sub_key], set):
                    knowledge_base[key][sub_key] = list(knowledge_base[key][sub_key])
    
    return knowledge_base


def extract_sections(text):
    """
    从文本中提取章节结构

    Args:
        text: 文档文本

    Returns:
        章节字典，键为章节标题，值为章节内容
    """
    # 匹配章节标题模式（如"1. 标题"，"一、标题"等）
    section_pattern = r'(?:(?:\d+\.)|(?:[一二三四五六七八九十]+、))\s*(.+?)\n'

    # 寻找所有章节标题及其位置
    section_matches = list(re.finditer(section_pattern, text))

    sections = {}

    # 提取每个章节的内容
    for i in range(len(section_matches)):
        title_match = section_matches[i]
        title = title_match.group(1).strip()

        # 确定章节内容的结束位置
        if i < len(section_matches) - 1:
            end_pos = section_matches[i + 1].start()
        else:
            end_pos = len(text)

        # 提取章节内容
        content = text[title_match.end():end_pos].strip()
        sections[title] = content

    return sections

def preprocess_data(documents, output_dir):
    """
    预处理文档数据并保存

    Args:
        documents: 文档列表
        output_dir: 输出目录

    Returns:
        预处理后的文档列表
    """
    os.makedirs(output_dir, exist_ok=True)

    preprocessed_docs = []

    for doc in tqdm(documents, desc="Preprocessing documents"):
        # 清洗文本
        doc['text'] = clean_text(doc['text'])

        # 提取章节
        doc['sections'] = extract_sections(doc['text'])

        # 保存预处理后的文档
        output_path = os.path.join(output_dir, f"{os.path.splitext(doc['file_name'])[0]}_preprocessed.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        preprocessed_docs.append(doc)

    return preprocessed_docs