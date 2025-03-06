import os
import re
import json
import random
from docx import Document
import pandas as pd
from tqdm import tqdm
import sys

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from doc_processor import DocProcessor

class DataPreprocessor:
    """数据预处理类，用于准备模型训练数据"""
    
    def __init__(self, data_dir="data", output_dir="data/labeled_data"):
        """
        初始化数据预处理器
        
        参数:
            data_dir: 原始数据目录
            output_dir: 输出目录
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.doc_processor = DocProcessor()
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
    
    def collect_docx_files(self):
        """收集所有docx文件"""
        docx_files = []
        for file in os.listdir(self.data_dir):
            if file.endswith(".docx") and not file.startswith("~$"):
                docx_files.append(os.path.join(self.data_dir, file))
        return docx_files
    
    def extract_sections(self, docx_files):
        """从文档中提取章节"""
        all_sections = []
        
        for file_path in tqdm(docx_files, desc="处理文档"):
            try:
                # 解析文档
                text = self.doc_processor.parse_docx(file_path)
                
                # 分割章节
                sections = self.doc_processor.split_into_sections(text)
                
                # 添加到结果中
                for section_title, section_text in sections.items():
                    all_sections.append({
                        "file": os.path.basename(file_path),
                        "section_title": section_title,
                        "section_text": section_text
                    })
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {e}")
        
        return all_sections
    
    def create_ner_training_data(self, sections, output_file="ner_training_data.json"):
        """
        创建命名实体识别训练数据
        
        这里我们使用一个简单的规则来模拟标注过程
        实际应用中应该使用人工标注的数据
        """
        ner_data = []
        
        # 定义实体类型和对应的正则表达式
        entity_patterns = {
            "物理状态名称": [
                r"器件标识",
                r"标识牢固度",
                r"封装类型",
                r"内部结构",
                r"封装材料",
                r"封装工艺",
                r"芯片装配结构",
                r"芯片粘接材料",
                r"芯片安装工艺",
                r"芯片结构和工艺",
                r"键合结构",
                r"键合丝材料与工艺"
            ],
            "典型物理状态值": [
                r"(DIP|CQFP|PLCC|TO|QFP|BGA|LCC|CSP)\d*",
                r"陶瓷封装",
                r"塑料封装",
                r"金属封装",
                r"玻璃熔封密封工艺",
                r"Ag浆",
                r"Au/Sn合金",
                r"Fe/Ni合金",
                r"CuAg焊料"
            ],
            "禁限用信息": [
                r"禁用",
                r"限用",
                r"不建议使用",
                r"不推荐使用",
                r"谨慎使用"
            ]
        }
        
        for section in tqdm(sections, desc="创建NER训练数据"):
            text = section["section_text"]
            entities = []
            
            # 使用正则表达式查找实体
            for entity_type, patterns in entity_patterns.items():
                for pattern in patterns:
                    for match in re.finditer(pattern, text):
                        start, end = match.span()
                        entity_text = match.group()
                        entities.append({
                            "start": start,
                            "end": end,
                            "text": entity_text,
                            "label": entity_type
                        })
            
            # 添加到训练数据
            if entities:
                ner_data.append({
                    "id": len(ner_data),
                    "text": text,
                    "entities": entities
                })
        
        # 保存训练数据
        output_path = os.path.join(self.output_dir, output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ner_data, f, ensure_ascii=False, indent=2)
        
        print(f"已保存NER训练数据到 {output_path}，共 {len(ner_data)} 条记录")
        return ner_data
    
    def create_relation_training_data(self, sections, output_file="relation_training_data.json"):
        """
        创建关系抽取训练数据
        
        这里我们使用一个简单的规则来模拟标注过程
        实际应用中应该使用人工标注的数据
        """
        relation_data = []
        
        # 定义关系类型和对应的模式
        relation_patterns = {
            "包含": r'(.{2,10})包[含括](.{2,10})',
            "采用": r'(.{2,10})采用(.{2,10})',
            "为": r'(.{2,10})为(.{2,10})',
            "是": r'(.{2,10})是(.{2,10})',
            "具有": r'(.{2,10})具有(.{2,10})',
            "属于": r'(.{2,10})属于(.{2,10})'
        }
        
        for section in tqdm(sections, desc="创建关系训练数据"):
            text = section["section_text"]
            relations = []
            
            # 使用正则表达式查找关系
            for relation_type, pattern in relation_patterns.items():
                for match in re.finditer(pattern, text):
                    head_text = match.group(1).strip()
                    tail_text = match.group(2).strip()
                    
                    # 添加到关系列表
                    relations.append({
                        "head": head_text,
                        "tail": tail_text,
                        "type": relation_type
                    })
            
            # 添加到训练数据
            if relations:
                relation_data.append({
                    "id": len(relation_data),
                    "text": text,
                    "relations": relations
                })
        
        # 保存训练数据
        output_path = os.path.join(self.output_dir, output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(relation_data, f, ensure_ascii=False, indent=2)
        
        print(f"已保存关系训练数据到 {output_path}，共 {len(relation_data)} 条记录")
        return relation_data
    
    def split_train_dev_test(self, data, train_ratio=0.7, dev_ratio=0.15, test_ratio=0.15, 
                            output_prefix="ner"):
        """
        将数据集划分为训练集、验证集和测试集
        
        参数:
            data: 数据列表
            train_ratio: 训练集比例
            dev_ratio: 验证集比例
            test_ratio: 测试集比例
            output_prefix: 输出文件前缀
        """
        # 随机打乱数据
        random.shuffle(data)
        
        # 计算划分点
        train_size = int(len(data) * train_ratio)
        dev_size = int(len(data) * dev_ratio)
        
        # 划分数据
        train_data = data[:train_size]
        dev_data = data[train_size:train_size + dev_size]
        test_data = data[train_size + dev_size:]
        
        # 保存数据集
        for name, dataset in [("train", train_data), ("dev", dev_data), ("test", test_data)]:
            output_path = os.path.join(self.output_dir, f"{output_prefix}_{name}.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
            print(f"已保存{name}集到 {output_path}，共 {len(dataset)} 条记录")
    
    def process(self):
        """处理数据流程"""
        print("开始数据预处理...")
        
        # 收集文档
        docx_files = self.collect_docx_files()
        print(f"找到 {len(docx_files)} 个docx文件")
        
        # 提取章节
        sections = self.extract_sections(docx_files)
        print(f"提取了 {len(sections)} 个章节")
        
        # 创建NER训练数据
        ner_data = self.create_ner_training_data(sections)
        
        # 创建关系训练数据
        relation_data = self.create_relation_training_data(sections)
        
        # 划分数据集
        self.split_train_dev_test(ner_data, output_prefix="ner")
        self.split_train_dev_test(relation_data, output_prefix="relation")
        
        print("数据预处理完成！")

if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.process() 