import re
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, AutoModelForSequenceClassification
from transformers import pipeline
from typing import Dict, List, Tuple, Any

from .base_extractor import BaseExtractor

class InformationExtractor(BaseExtractor):
    """信息抽取类，负责从文本中提取关键信息"""
    
    def __init__(self, ner_model_path, relation_model_path):
        # 加载命名实体识别模型
        self.tokenizer = AutoTokenizer.from_pretrained(ner_model_path)
        self.ner_model = AutoModelForTokenClassification.from_pretrained(ner_model_path)
        
        # 加载关系抽取模型
        self.relation_model = AutoModelForSequenceClassification.from_pretrained(relation_model_path)
        
        # 创建NER流水线
        self.ner_pipeline = pipeline("ner", model=self.ner_model, tokenizer=self.tokenizer)
        
    def extract_entities(self, text):
        """提取命名实体"""
        results = self.ner_pipeline(text)
        
        # 合并分词后的实体
        entities = []
        current_entity = None
        
        for item in results:
            if current_entity and current_entity["entity"] != item["entity"]:
                entities.append(current_entity)
                current_entity = None
            
            if current_entity:
                current_entity["word"] += item["word"].replace("##", "")
                current_entity["end"] = item["end"]
            else:
                current_entity = item.copy()
            
        if current_entity:
            entities.append(current_entity)
        
        return entities
    
    def extract_relations(self, text, entities):
        """提取实体间关系"""
        relations = []
        
        # 对实体对进行关系分类
        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if i != j:
                    # 构造输入
                    inputs = self.tokenizer(
                        text,
                        text.replace(e1["word"], f"[E1]{e1['word']}[/E1]").replace(e2["word"], f"[E2]{e2['word']}[/E2]"),
                        return_tensors="pt"
                    )
                    
                    # 预测关系
                    with torch.no_grad():
                        outputs = self.relation_model(**inputs)
                        predicted_class = outputs.logits.argmax().item()
                    
                    # 如果预测为有关系
                    if predicted_class != 0:  # 假设0表示"无关系"
                        relations.append({
                            "head": e1,
                            "tail": e2,
                            "relation_type": predicted_class  # 实际应用中应映射到具体关系标签
                        })
        
        return relations
    
    def extract_info(self, text, section_type):
        """根据章节类型提取关键信息"""
        # 根据不同章节类型使用不同的提取逻辑
        if "标识部分" in section_type:
            return self._extract_identification_info(text)
        elif "封装结构" in section_type:
            return self._extract_package_info(text)
        elif "芯片" in section_type:
            return self._extract_chip_info(text)
        elif "键合系统" in section_type:
            return self._extract_bonding_info(text)
        else:
            # 默认提取方法
            return self._extract_general_info(text)
    
    def _extract_identification_info(self, text):
        """提取标识信息"""
        info = {
            "型号规格": None,
            "生产批次": None,
            "生产厂标识": None,
            "标识方式": None,
            "标识牢固度": None,
            "问题与建议": []
        }
        
        # 型号规格提取
        model_pattern = r"型号规格[（\(]([^）\)]+)[）\)]"
        model_match = re.search(model_pattern, text)
        if model_match:
            info["型号规格"] = model_match.group(1)
        
        # 生产批次提取
        batch_pattern = r"生产批次[（\(]([^）\)]+)[）\)]"
        batch_match = re.search(batch_pattern, text)
        if batch_match:
            info["生产批次"] = batch_match.group(1)
        
        # 生产厂标识提取
        vendor_pattern = r"生产厂标识[（\(]([^）\)]+)[）\)]"
        vendor_match = re.search(vendor_pattern, text)
        if vendor_match:
            info["生产厂标识"] = vendor_match.group(1)
        
        # 标识方式提取
        method_pattern = r"器件采用([\S]+)方式打标"
        method_match = re.search(method_pattern, text)
        if method_match:
            info["标识方式"] = method_match.group(1)
        
        # 标识牢固度评估
        durability_pattern = r"标识牢固度([^，。；]+)"
        durability_match = re.search(durability_pattern, text)
        if durability_match:
            info["标识牢固度"] = durability_match.group(1).strip()
        
        # 问题与建议提取
        suggestion_pattern = r"建议([^。；]+)"
        for match in re.finditer(suggestion_pattern, text):
            info["问题与建议"].append(match.group(1).strip())
        
        return info
    
    def _extract_package_info(self, text):
        """提取封装信息"""
        # 实现封装信息提取逻辑
        info = {
            "封装类型": None,
            "封装材料": [],
            "封装工艺": None,
            "质量评估": None
        }
        
        # 封装类型提取
        type_pattern = r"器件采用([A-Z0-9]+)([^，。；]+)"
        type_match = re.search(type_pattern, text)
        if type_match:
            info["封装类型"] = type_match.group(1)
        
        # 封装材料提取
        material_patterns = [
            r"([^，。；]+材料为[^，。；]+)",
            r"([^，。；]+采用[^，。；]+材料)"
        ]
        
        for pattern in material_patterns:
            for match in re.finditer(pattern, text):
                info["封装材料"].append(match.group(1).strip())
        
        # 封装工艺提取
        process_pattern = r"采用([^，。；]+工艺)"
        for match in re.finditer(process_pattern, text):
            info["封装工艺"] = match.group(1).strip()
        
        # 质量评估提取
        quality_patterns = [
            r"工艺([良好|优良|正常|合格]+)",
            r"质量([良好|优良|正常|合格]+)"
        ]
        
        for pattern in quality_patterns:
            match = re.search(pattern, text)
            if match:
                info["质量评估"] = match.group(1).strip()
                break
        
        return info
    
    def _extract_chip_info(self, text):
        """提取芯片信息"""
        info = {
            "芯片装配结构": None,
            "芯片粘接材料": None,
            "芯片安装工艺": None,
            "芯片结构评估": None,
            "问题与建议": []
        }
        
        # 芯片装配结构提取
        structure_patterns = [
            r"芯片(采用[^，。；]+装配结构)",
            r"芯片(装配[^，。；]+结构)",
            r"(芯片[^，。；]+安装方式)"
        ]
        
        for pattern in structure_patterns:
            match = re.search(pattern, text)
            if match:
                info["芯片装配结构"] = match.group(1).strip()
                break
        
        # 芯片粘接材料提取
        material_patterns = [
            r"芯片粘接材料为([^，。；]+)",
            r"采用([^，。；]+)粘接芯片",
            r"芯片采用([^，。；]+)粘接"
        ]
        
        for pattern in material_patterns:
            match = re.search(pattern, text)
            if match:
                info["芯片粘接材料"] = match.group(1).strip()
                break
        
        # 芯片安装工艺提取
        process_patterns = [
            r"芯片安装采用([^，。；]+工艺)",
            r"芯片([^，。；]+安装工艺)",
            r"采用([^，。；]+)安装芯片"
        ]
        
        for pattern in process_patterns:
            match = re.search(pattern, text)
            if match:
                info["芯片安装工艺"] = match.group(1).strip()
                break
        
        # 芯片结构评估提取
        quality_patterns = [
            r"芯片结构([良好|优良|正常|合格]+)",
            r"芯片安装质量([^，。；]+)",
            r"芯片工艺([^，。；]+)"
        ]
        
        for pattern in quality_patterns:
            match = re.search(pattern, text)
            if match:
                info["芯片结构评估"] = match.group(1).strip()
                break
        
        # 问题与建议提取
        suggestion_patterns = [
            r"建议([^。；]+)",
            r"存在问题([^。；]+)",
            r"需要改进([^。；]+)"
        ]
        
        for pattern in suggestion_patterns:
            for match in re.finditer(pattern, text):
                info["问题与建议"].append(match.group(1).strip())
        
        return info
    
    def _extract_bonding_info(self, text):
        """提取键合信息"""
        info = {
            "键合结构": None,
            "键合丝材料": None,
            "键合工艺": None,
            "键合质量评估": None,
            "问题与建议": []
        }
        
        # 键合结构提取
        structure_patterns = [
            r"键合(采用[^，。；]+结构)",
            r"(键合[^，。；]+结构)",
            r"(采用[^，。；]+键合结构)"
        ]
        
        for pattern in structure_patterns:
            match = re.search(pattern, text)
            if match:
                info["键合结构"] = match.group(1).strip()
                break
        
        # 键合丝材料提取
        material_patterns = [
            r"键合丝材料为([^，。；]+)",
            r"采用([^，。；]+)键合丝",
            r"键合丝采用([^，。；]+)"
        ]
        
        for pattern in material_patterns:
            match = re.search(pattern, text)
            if match:
                info["键合丝材料"] = match.group(1).strip()
                break
        
        # 键合工艺提取
        process_patterns = [
            r"键合采用([^，。；]+工艺)",
            r"([^，。；]+键合工艺)",
            r"采用([^，。；]+)进行键合"
        ]
        
        for pattern in process_patterns:
            match = re.search(pattern, text)
            if match:
                info["键合工艺"] = match.group(1).strip()
                break
        
        # 键合质量评估提取
        quality_patterns = [
            r"键合质量([良好|优良|正常|合格]+)",
            r"键合([^，。；]+质量)",
            r"键合工艺([^，。；]+)"
        ]
        
        for pattern in quality_patterns:
            match = re.search(pattern, text)
            if match:
                info["键合质量评估"] = match.group(1).strip()
                break
        
        # 问题与建议提取
        suggestion_patterns = [
            r"建议([^。；]+)",
            r"存在问题([^。；]+)",
            r"需要改进([^。；]+)"
        ]
        
        for pattern in suggestion_patterns:
            for match in re.finditer(pattern, text):
                info["问题与建议"].append(match.group(1).strip())
        
        return info
    
    def _extract_general_info(self, text):
        """提取通用信息"""
        info = {
            "关键技术参数": [],
            "工艺特点": [],
            "质量评估": None,
            "问题与建议": []
        }
        
        # 提取关键技术参数
        param_patterns = [
            r"([^，。；]+参数为[^，。；]+)",
            r"([^，。；]+指标为[^，。；]+)",
            r"([^，。；]+数值为[^，。；]+)"
        ]
        
        for pattern in param_patterns:
            for match in re.finditer(pattern, text):
                info["关键技术参数"].append(match.group(1).strip())
        
        # 提取工艺特点
        process_patterns = [
            r"([^，。；]+工艺特点[^，。；]*)",
            r"(采用[^，。；]+工艺)",
            r"(工艺[^，。；]+特点)"
        ]
        
        for pattern in process_patterns:
            for match in re.finditer(pattern, text):
                info["工艺特点"].append(match.group(1).strip())
        
        # 提取质量评估
        quality_patterns = [
            r"质量([良好|优良|正常|合格]+)",
            r"([^，。；]+质量评估结果)",
            r"评估结果([^，。；]+)"
        ]
        
        for pattern in quality_patterns:
            match = re.search(pattern, text)
            if match:
                info["质量评估"] = match.group(1).strip()
                break
        
        # 提取问题与建议
        suggestion_patterns = [
            r"建议([^。；]+)",
            r"存在问题([^。；]+)",
            r"需要改进([^。；]+)"
        ]
        
        for pattern in suggestion_patterns:
            for match in re.finditer(pattern, text):
                info["问题与建议"].append(match.group(1).strip())
        
        return info 