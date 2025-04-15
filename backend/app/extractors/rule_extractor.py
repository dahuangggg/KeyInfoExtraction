import re
import jieba
import jieba.posseg as pseg
import os
import json
from typing import Dict, List, Tuple, Any, Optional, Set
# import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, AutoModelForSequenceClassification
from transformers import pipeline

from .base_extractor import BaseExtractor

class InformationExtractor(BaseExtractor):
    """信息抽取类，负责从文本中提取关键信息"""
    
    def __init__(self, ner_model_path=None, relation_model_path=None, use_models=False):
        """
        初始化信息抽取器
        
        Args:
            ner_model_path: 命名实体识别模型路径，如果为None则使用规则提取
            relation_model_path: 关系抽取模型路径，如果为None则使用规则提取
            use_models: 是否使用模型进行提取，如果为False则仅使用规则提取
        """
        self.use_models = use_models
        self.ner_model = None
        self.relation_model = None
        self.tokenizer = None
        self.ner_pipeline = None
        
        # 加载停用词
        self.stopwords = self._load_stopwords()
        
        # 加载专有名词词典
        self.load_custom_dict()
        
        # 如果指定了模型路径且use_models为True，则加载模型
        if use_models and ner_model_path and relation_model_path:
            try:
                # 加载命名实体识别模型
                self.tokenizer = AutoTokenizer.from_pretrained(ner_model_path)
                self.ner_model = AutoModelForTokenClassification.from_pretrained(ner_model_path)
                
                # 加载关系抽取模型
                self.relation_model = AutoModelForSequenceClassification.from_pretrained(relation_model_path)
                
                # 创建NER流水线
                self.ner_pipeline = pipeline("ner", model=self.ner_model, tokenizer=self.tokenizer)
                print("成功加载NER和关系抽取模型")
            except Exception as e:
                print(f"加载模型失败: {e}")
                print("将使用规则提取")
                self.use_models = False
    
    def _load_stopwords(self) -> Set[str]:
        """加载停用词表"""
        stopwords = set()
        try:
            # 尝试加载停用词表
            stopwords_path = os.path.join(os.path.dirname(__file__), '../data/stopwords.txt')
            if os.path.exists(stopwords_path):
                with open(stopwords_path, 'r', encoding='utf-8') as f:
                    stopwords = set([line.strip() for line in f.readlines()])
        except Exception as e:
            print(f"加载停用词表失败: {e}")
            # 使用一些基本的停用词
            stopwords = set(['的', '了', '和', '与', '或', '是', '在', '有', '为', '以', '及', '等', '对', '中'])
        
        return stopwords
    
    def load_custom_dict(self):
        """加载自定义词典"""
        try:
            # 尝试加载自定义词典
            custom_dict_path = os.path.join(os.path.dirname(__file__), '../data/custom_dict.txt')
            if os.path.exists(custom_dict_path):
                jieba.load_userdict(custom_dict_path)
                print("成功加载自定义词典")
        except Exception as e:
            print(f"加载自定义词典失败: {e}")
    
    def segment_text(self, text: str) -> List[str]:
        """
        对文本进行分句
        
        Args:
            text: 输入文本
            
        Returns:
            分句后的文本列表
        """
        # 分句规则
        patterns = [
            r'([。！？\?])([^\"\'])',
            r'(\.{6})([^\"\'])',
            r'(\…{2})([^\"\'])',
            r'([。！？\?][\"\'])([^，。！？\?])'
        ]
        
        # 应用分句规则
        for pattern in patterns:
            text = re.sub(pattern, r'\1\n\2', text)
        
        # 分割成句子
        sentences = text.rstrip().split('\n')
        
        return sentences
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        提取命名实体
        
        Args:
            text: 输入文本
            
        Returns:
            实体列表
        """
        if self.use_models and self.ner_pipeline:
            # 使用模型提取实体
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
        else:
            # 使用规则提取实体
            entities = []
            sentences = self.segment_text(text)
            
            for sentence in sentences:
                # 使用jieba进行分词和词性标注
                words = pseg.cut(sentence)
                
                for word, flag in words:
                    if word in self.stopwords or word.isspace():
                        continue
                    
                    # 根据词性判断是否为实体
                    if flag in ['n', 'nz', 'nr', 'ns', 'nt', 'x']:
                        start = sentence.find(word)
                        if start != -1:
                            entities.append({
                                "word": word,
                                "entity": flag,
                                "start": start,
                                "end": start + len(word)
                            })
            
            return entities
    
    def extract_relations(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        提取实体间关系
        
        Args:
            text: 输入文本
            entities: 实体列表
            
        Returns:
            关系列表
        """
        if self.use_models and self.relation_model and self.tokenizer:
            # 使用模型提取关系
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
        else:
            # 使用规则提取关系
            relations = []
            sentences = self.segment_text(text)
            
            # 定义关系模式
            relation_patterns = {
                "包含": r'(.+)包[含括](.+)',
                "采用": r'(.+)采用(.+)',
                "为": r'(.+)为(.+)',
                "是": r'(.+)是(.+)',
                "具有": r'(.+)具有(.+)',
                "属于": r'(.+)属于(.+)'
            }
            
            for sentence in sentences:
                for relation_type, pattern in relation_patterns.items():
                    matches = re.finditer(pattern, sentence)
                    for match in matches:
                        head_text = match.group(1).strip()
                        tail_text = match.group(2).strip()
                        
                        # 查找匹配的实体
                        head_entity = None
                        tail_entity = None
                        
                        for entity in entities:
                            if entity["word"] in head_text:
                                head_entity = entity
                            if entity["word"] in tail_text:
                                tail_entity = entity
                        
                        if head_entity and tail_entity:
                            relations.append({
                                "head": head_entity,
                                "tail": tail_entity,
                                "relation_type": relation_type
                            })
            
            return relations
    
    def extract_info(self, text: str, section_type: str) -> Dict[str, Any]:
        """
        根据章节类型提取关键信息
        
        Args:
            text: 待提取的文本
            section_type: 章节类型
            
        Returns:
            包含提取信息的字典
        """
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
    
    def _extract_identification_info(self, text: str) -> Dict[str, Any]:
        """
        提取标识信息
        
        Args:
            text: 输入文本
            
        Returns:
            标识信息字典
        """
        info = {
            "型号规格": None,
            "生产批次": None,
            "生产厂标识": None,
            "标识方式": None,
            "标识牢固度": None,
            "问题与建议": []
        }
        
        # 型号规格提取
        model_patterns = [
            r"型号规格[（\(]([^）\)]+)[）\)]",
            r"型号规格为([^，。；]+)",
            r"器件型号[为是]([^，。；]+)",
            r"器件型号规格为([^，。；]+)"
        ]
        
        for pattern in model_patterns:
            model_match = re.search(pattern, text)
            if model_match:
                info["型号规格"] = model_match.group(1).strip()
                break
        
        # 生产批次提取
        batch_patterns = [
            r"生产批次[（\(]([^）\)]+)[）\)]",
            r"生产批次为([^，。；]+)",
            r"批次[为号]([^，。；]+)",
            r"生产批[号次][为是]([^，。；]+)"
        ]
        
        for pattern in batch_patterns:
            batch_match = re.search(pattern, text)
            if batch_match:
                info["生产批次"] = batch_match.group(1).strip()
                break
        
        # 生产厂标识提取
        vendor_patterns = [
            r"生产厂标识[（\(]([^）\)]+)[）\)]",
            r"生产厂标识为([^，。；]+)",
            r"厂家标识[为是]([^，。；]+)",
            r"生产厂[为是]([^，。；]+)"
        ]
        
        for pattern in vendor_patterns:
            vendor_match = re.search(pattern, text)
            if vendor_match:
                info["生产厂标识"] = vendor_match.group(1).strip()
                break
        
        # 标识方式提取
        method_patterns = [
            r"器件采用([\S]+)方式打标",
            r"标识采用([\S]+)方式",
            r"采用([\S]+)[打印刻]标",
            r"标识方式[为是]([\S]+)"
        ]
        
        for pattern in method_patterns:
            method_match = re.search(pattern, text)
            if method_match:
                info["标识方式"] = method_match.group(1).strip()
                break
        
        # 标识牢固度评估
        durability_patterns = [
            r"标识牢固度([^，。；]+)",
            r"标识牢固[性度][为是]([^，。；]+)",
            r"标识[为是]([^，。；]*牢固[^，。；]*)"
        ]
        
        for pattern in durability_patterns:
            durability_match = re.search(pattern, text)
            if durability_match:
                info["标识牢固度"] = durability_match.group(1).strip()
                break
        
        # 问题与建议提取
        suggestion_patterns = [
            r"建议([^。；]+)",
            r"存在[的]?问题[：:]([^。；]+)",
            r"缺少([^，。；]+)",
            r"问题[为是]([^。；]+)"
        ]
        
        for pattern in suggestion_patterns:
            for match in re.finditer(pattern, text):
                suggestion = match.group(1).strip()
                if suggestion and suggestion not in info["问题与建议"]:
                    info["问题与建议"].append(suggestion)
        
        # 处理未提取到的字段
        for key in info:
            if key != "问题与建议" and not info[key]:
                info[key] = "文中未提及"
        
        return info
    
    def _extract_package_info(self, text: str) -> Dict[str, Any]:
        """
        提取封装信息
        
        Args:
            text: 输入文本
            
        Returns:
            封装信息字典
        """
        info = {
            "封装类型": None,
            "封装材料": [],
            "封装工艺": None,
            "质量评估": None
        }
        
        # 封装类型提取
        type_patterns = [
            r"器件采用([A-Z0-9]+[^，。；]*)[封装]",
            r"封装类型[为是]([^，。；]+)",
            r"采用([^，。；]+)封装",
            r"([A-Z0-9]+\d+[A-Z]*)[^，。；]*封装"
        ]
        
        for pattern in type_patterns:
            type_match = re.search(pattern, text)
            if type_match:
                info["封装类型"] = type_match.group(1).strip()
                break
        
        # 封装材料提取
        material_patterns = [
            r"封装材料[为包括含]([^，。；]+)",
            r"封装材料主要包括([^，。；]+)",
            r"材料[为包括含]([^，。；]+)",
            r"([^，。；]+材料[为是][^，。；]+)"
        ]
        
        for pattern in material_patterns:
            material_match = re.search(pattern, text)
            if material_match:
                materials_text = material_match.group(1).strip()
                # 分割多个材料
                materials = [m.strip() for m in re.split(r'[、和及]', materials_text) if m.strip()]
                if materials:
                    info["封装材料"] = materials
                break
        
        # 封装工艺提取
        process_patterns = [
            r"封装工艺[为是采用]([^，。；]+)",
            r"采用([^，。；]+)工艺",
            r"工艺[为是]([^，。；]+)",
            r"([^，。；]+)[工艺技术][^，。；]*封装"
        ]
        
        for pattern in process_patterns:
            process_match = re.search(pattern, text)
            if process_match:
                info["封装工艺"] = process_match.group(1).strip()
                break
        
        # 质量评估提取
        quality_patterns = [
            r"质量评估[为是]([^，。；]+)",
            r"工艺质量[为是]([^，。；]+)",
            r"质量[为是]([^，。；]+)",
            r"评估[为是]([^，。；]+)"
        ]
        
        for pattern in quality_patterns:
            quality_match = re.search(pattern, text)
            if quality_match:
                info["质量评估"] = quality_match.group(1).strip()
                break
        
        # 处理未提取到的字段
        for key in info:
            if key != "封装材料" and not info[key]:
                info[key] = "文中未提及"
            elif key == "封装材料" and not info[key]:
                info[key] = ["文中未提及"]
        
        return info
    
    def _extract_chip_info(self, text: str) -> Dict[str, Any]:
        """
        提取芯片信息
        
        Args:
            text: 输入文本
            
        Returns:
            芯片信息字典
        """
        info = {
            "芯片装配结构": None,
            "芯片粘接材料": None,
            "芯片安装工艺": None,
            "芯片结构和工艺": None,
            "问题与建议": []
        }
        
        # 芯片装配结构提取
        structure_patterns = [
            r"芯片装配结构[为是]([^，。；]+)",
            r"芯片[为是]([^，。；]*结构[^，。；]*)",
            r"装配结构[为是]([^，。；]+)",
            r"([^，。；]+)结构[^，。；]*芯片"
        ]
        
        for pattern in structure_patterns:
            structure_match = re.search(pattern, text)
            if structure_match:
                info["芯片装配结构"] = structure_match.group(1).strip()
                break
        
        # 芯片粘接材料提取
        material_patterns = [
            r"芯片粘接材料[为是]([^，。；]+)",
            r"粘接材料[为是]([^，。；]+)",
            r"采用([^，。；]+)粘接芯片",
            r"芯片采用([^，。；]+)粘接"
        ]
        
        for pattern in material_patterns:
            material_match = re.search(pattern, text)
            if material_match:
                info["芯片粘接材料"] = material_match.group(1).strip()
                break
        
        # 芯片安装工艺提取
        process_patterns = [
            r"芯片安装工艺[为是采用]([^，。；]+)",
            r"安装工艺[为是]([^，。；]+)",
            r"芯片安装采用([^，。；]+)",
            r"采用([^，。；]+)安装芯片"
        ]
        
        for pattern in process_patterns:
            process_match = re.search(pattern, text)
            if process_match:
                info["芯片安装工艺"] = process_match.group(1).strip()
                break
        
        # 芯片结构和工艺提取
        tech_patterns = [
            r"芯片结构[为是采用]([^，。；]+)",
            r"芯片[^，。；]*工艺[为是]([^，。；]+)",
            r"结构和工艺[为是]([^，。；]+)",
            r"芯片采用([^，。；]+)工艺"
        ]
        
        for pattern in tech_patterns:
            tech_match = re.search(pattern, text)
            if tech_match:
                info["芯片结构和工艺"] = tech_match.group(1).strip()
                break
        
        # 问题与建议提取
        suggestion_patterns = [
            r"建议([^。；]+)",
            r"存在[的]?问题[：:]([^。；]+)",
            r"缺少([^，。；]+)",
            r"问题[为是]([^。；]+)"
        ]
        
        for pattern in suggestion_patterns:
            for match in re.finditer(pattern, text):
                suggestion = match.group(1).strip()
                if suggestion and suggestion not in info["问题与建议"]:
                    info["问题与建议"].append(suggestion)
        
        # 处理未提取到的字段
        for key in info:
            if key != "问题与建议" and not info[key]:
                info[key] = "文中未提及"
        
        return info
    
    def _extract_bonding_info(self, text: str) -> Dict[str, Any]:
        """
        提取键合信息
        
        Args:
            text: 输入文本
            
        Returns:
            键合信息字典
        """
        info = {
            "键合结构": None,
            "键合丝材料": None,
            "键合工艺": None,
            "键合质量评估": None,
            "问题与建议": []
        }
        
        # 键合结构提取
        structure_patterns = [
            r"键合结构[为是]([^，。；]+)",
            r"键合[为是]([^，。；]*结构[^，。；]*)",
            r"([^，。；]+)结构[^，。；]*键合",
            r"采用([^，。；]+)键合结构"
        ]
        
        for pattern in structure_patterns:
            structure_match = re.search(pattern, text)
            if structure_match:
                info["键合结构"] = structure_match.group(1).strip()
                break
        
        # 键合丝材料提取
        material_patterns = [
            r"键合丝[为是材料]([^，。；]+)",
            r"键合材料[为是]([^，。；]+)",
            r"采用([^，。；]+)键合丝",
            r"([^，。；]+)丝[^，。；]*键合"
        ]
        
        for pattern in material_patterns:
            material_match = re.search(pattern, text)
            if material_match:
                info["键合丝材料"] = material_match.group(1).strip()
                break
        
        # 键合工艺提取
        process_patterns = [
            r"键合工艺[为是采用]([^，。；]+)",
            r"键合采用([^，。；]+)工艺",
            r"采用([^，。；]+)键合工艺",
            r"工艺[为是]([^，。；]*键合[^，。；]*)"
        ]
        
        for pattern in process_patterns:
            process_match = re.search(pattern, text)
            if process_match:
                info["键合工艺"] = process_match.group(1).strip()
                break
        
        # 键合质量评估提取
        quality_patterns = [
            r"键合质量[为是]([^，。；]+)",
            r"键合[^，。；]*评估[为是]([^，。；]+)",
            r"质量评估[为是]([^，。；]*键合[^，。；]*)",
            r"键合[^，。；]*质量([^，。；]+)"
        ]
        
        for pattern in quality_patterns:
            quality_match = re.search(pattern, text)
            if quality_match:
                info["键合质量评估"] = quality_match.group(1).strip()
                break
        
        # 问题与建议提取
        suggestion_patterns = [
            r"建议([^。；]+)",
            r"存在[的]?问题[：:]([^。；]+)",
            r"缺少([^，。；]+)",
            r"问题[为是]([^。；]+)"
        ]
        
        for pattern in suggestion_patterns:
            for match in re.finditer(pattern, text):
                suggestion = match.group(1).strip()
                if suggestion and suggestion not in info["问题与建议"]:
                    info["问题与建议"].append(suggestion)
        
        # 处理未提取到的字段
        for key in info:
            if key != "问题与建议" and not info[key]:
                info[key] = "文中未提及"
        
        return info
    
    def _extract_general_info(self, text: str) -> Dict[str, Any]:
        """
        提取通用信息
        
        Args:
            text: 输入文本
            
        Returns:
            通用信息字典
        """
        # 提取实体和关系
        entities = self.extract_entities(text)
        relations = self.extract_relations(text, entities)
        
        # 构建信息字典
        info = {
            "实体": [entity["word"] for entity in entities],
            "关系": []
        }
        
        # 添加关系信息
        for relation in relations:
            info["关系"].append({
                "头实体": relation["head"]["word"],
                "尾实体": relation["tail"]["word"],
                "关系类型": relation["relation_type"]
            })
        
        # 提取关键词
        keywords = self._extract_keywords(text)
        info["关键词"] = keywords
        
        # 提取问题与建议
        suggestions = []
        suggestion_patterns = [
            r"建议([^。；]+)",
            r"存在[的]?问题[：:]([^。；]+)",
            r"缺少([^，。；]+)",
            r"问题[为是]([^。；]+)"
        ]
        
        for pattern in suggestion_patterns:
            for match in re.finditer(pattern, text):
                suggestion = match.group(1).strip()
                if suggestion and suggestion not in suggestions:
                    suggestions.append(suggestion)
        
        info["问题与建议"] = suggestions
        
        return info
    
    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        提取文本中的关键词
        
        Args:
            text: 输入文本
            top_n: 返回的关键词数量
            
        Returns:
            关键词列表
        """
        # 分词
        words = jieba.cut(text)
        
        # 过滤停用词
        filtered_words = [word for word in words if word not in self.stopwords and len(word) > 1]
        
        # 统计词频
        word_freq = {}
        for word in filtered_words:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1
        
        # 按词频排序
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # 返回前top_n个关键词
        return [word for word, _ in sorted_words[:top_n]] 