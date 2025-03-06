import os
import json
import argparse
import numpy as np
from tqdm import tqdm
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, AutoModelForSequenceClassification
from seqeval.metrics import classification_report as ner_classification_report
from sklearn.metrics import classification_report as relation_classification_report
import sys

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from doc_processor import DocProcessor

class ModelEvaluator:
    """模型评估类"""
    
    def __init__(self, ner_model_path, relation_model_path):
        """
        初始化评估器
        
        参数:
            ner_model_path: NER模型路径
            relation_model_path: 关系抽取模型路径
        """
        self.ner_model_path = ner_model_path
        self.relation_model_path = relation_model_path
        self.doc_processor = DocProcessor()
        
        # 加载NER模型
        print(f"加载NER模型: {ner_model_path}")
        self.ner_tokenizer = AutoTokenizer.from_pretrained(ner_model_path)
        self.ner_model = AutoModelForTokenClassification.from_pretrained(ner_model_path)
        
        # 加载标签映射
        with open(os.path.join(ner_model_path, "label2id.json"), 'r', encoding='utf-8') as f:
            self.label2id = json.load(f)
            self.id2label = {int(v): k for k, v in self.label2id.items()}
        
        # 加载关系抽取模型
        print(f"加载关系抽取模型: {relation_model_path}")
        self.relation_tokenizer = AutoTokenizer.from_pretrained(relation_model_path)
        self.relation_model = AutoModelForSequenceClassification.from_pretrained(relation_model_path)
        
        # 加载关系映射
        with open(os.path.join(relation_model_path, "relation2id.json"), 'r', encoding='utf-8') as f:
            self.relation2id = json.load(f)
            self.id2relation = {int(v): k for k, v in self.relation2id.items()}
    
    def evaluate_ner(self, test_file):
        """
        评估NER模型
        
        参数:
            test_file: 测试数据文件
        """
        print(f"评估NER模型，使用测试文件: {test_file}")
        
        # 加载测试数据
        with open(test_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        all_true_labels = []
        all_pred_labels = []
        
        # 设置模型为评估模式
        self.ner_model.eval()
        
        for item in tqdm(test_data, desc="评估NER"):
            text = item["text"]
            true_entities = item["entities"]
            
            # 提取真实标签
            true_labels = ["O"] * len(text)
            for entity in true_entities:
                start = entity["start"]
                end = entity["end"]
                label = entity["label"]
                
                true_labels[start] = f"B-{label}"
                for i in range(start + 1, end):
                    true_labels[i] = f"I-{label}"
            
            # 使用模型预测
            inputs = self.ner_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.ner_model(**inputs)
            
            # 获取预测结果
            predictions = outputs.logits.argmax(dim=2)[0].tolist()
            tokens = self.ner_tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
            
            # 将预测结果映射回原始文本
            pred_labels = []
            token_idx = 0
            for i, token in enumerate(tokens):
                if token in ["[CLS]", "[SEP]", "[PAD]"]:
                    continue
                
                if token.startswith("##"):
                    continue
                
                if token_idx < len(text):
                    pred_label = self.id2label[predictions[i]]
                    pred_labels.append(pred_label)
                    token_idx += 1
            
            # 确保预测标签长度与文本长度一致
            pred_labels = pred_labels[:len(text)]
            if len(pred_labels) < len(text):
                pred_labels.extend(["O"] * (len(text) - len(pred_labels)))
            
            all_true_labels.append(true_labels)
            all_pred_labels.append(pred_labels)
        
        # 计算评估指标
        print("\nNER评估结果:")
        print(ner_classification_report(all_true_labels, all_pred_labels))
    
    def evaluate_relation(self, test_file):
        """
        评估关系抽取模型
        
        参数:
            test_file: 测试数据文件
        """
        print(f"评估关系抽取模型，使用测试文件: {test_file}")
        
        # 加载测试数据
        with open(test_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        all_true_relations = []
        all_pred_relations = []
        
        # 设置模型为评估模式
        self.relation_model.eval()
        
        for item in tqdm(test_data, desc="评估关系抽取"):
            text = item["text"]
            relations = item["relations"]
            
            for relation in relations:
                head = relation["head"]
                tail = relation["tail"]
                true_relation = relation["type"]
                
                # 标记头尾实体
                marked_text = text.replace(head, f"[HEAD]{head}[/HEAD]", 1)
                marked_text = marked_text.replace(tail, f"[TAIL]{tail}[/TAIL]", 1)
                
                # 使用模型预测
                inputs = self.relation_tokenizer(marked_text, return_tensors="pt", truncation=True, max_length=512)
                with torch.no_grad():
                    outputs = self.relation_model(**inputs)
                
                # 获取预测结果
                prediction = outputs.logits.argmax(dim=1)[0].item()
                pred_relation = self.id2relation[prediction]
                
                all_true_relations.append(true_relation)
                all_pred_relations.append(pred_relation)
        
        # 计算评估指标
        print("\n关系抽取评估结果:")
        print(relation_classification_report(all_true_relations, all_pred_relations))
    
    def evaluate_on_document(self, doc_path):
        """
        在完整文档上评估模型
        
        参数:
            doc_path: 文档路径
        """
        print(f"在文档上评估模型: {doc_path}")
        
        # 解析文档
        text = self.doc_processor.parse_docx(doc_path)
        
        # 分割章节
        sections = self.doc_processor.split_into_sections(text)
        
        for section_title, section_text in sections.items():
            print(f"\n处理章节: {section_title}")
            
            # NER预测
            print("执行命名实体识别...")
            entities = self._predict_entities(section_text)
            
            # 关系抽取预测
            print("执行关系抽取...")
            relations = self._predict_relations(section_text, entities)
            
            # 打印结果
            print("\n识别到的实体:")
            for entity in entities:
                print(f"  - {entity['text']} ({entity['label']})")
            
            print("\n识别到的关系:")
            for relation in relations:
                print(f"  - {relation['head']} {relation['type']} {relation['tail']}")
    
    def _predict_entities(self, text):
        """
        预测文本中的实体
        
        参数:
            text: 输入文本
            
        返回:
            实体列表
        """
        # 分段处理长文本
        max_length = 510  # 留出[CLS]和[SEP]的位置
        entities = []
        
        for i in range(0, len(text), max_length):
            segment = text[i:i+max_length]
            
            # 使用模型预测
            inputs = self.ner_tokenizer(segment, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.ner_model(**inputs)
            
            # 获取预测结果
            predictions = outputs.logits.argmax(dim=2)[0].tolist()
            tokens = self.ner_tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
            
            # 解析预测结果
            current_entity = None
            for j, (token, pred) in enumerate(zip(tokens, predictions)):
                if token in ["[CLS]", "[SEP]", "[PAD]"]:
                    continue
                
                pred_label = self.id2label[pred]
                
                if pred_label.startswith("B-"):
                    if current_entity:
                        entities.append(current_entity)
                    
                    entity_type = pred_label[2:]
                    current_entity = {
                        "start": i + j - 1,  # 减去[CLS]
                        "text": token,
                        "label": entity_type
                    }
                elif pred_label.startswith("I-") and current_entity:
                    current_entity["text"] += token.replace("##", "")
                else:
                    if current_entity:
                        entities.append(current_entity)
                        current_entity = None
            
            if current_entity:
                entities.append(current_entity)
        
        return entities
    
    def _predict_relations(self, text, entities):
        """
        预测实体间的关系
        
        参数:
            text: 输入文本
            entities: 实体列表
            
        返回:
            关系列表
        """
        relations = []
        
        # 对实体对进行关系分类
        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if i != j:
                    head = e1["text"]
                    tail = e2["text"]
                    
                    # 标记头尾实体
                    marked_text = text.replace(head, f"[HEAD]{head}[/HEAD]", 1)
                    marked_text = marked_text.replace(tail, f"[TAIL]{tail}[/TAIL]", 1)
                    
                    # 使用模型预测
                    inputs = self.relation_tokenizer(marked_text, return_tensors="pt", truncation=True, max_length=512)
                    with torch.no_grad():
                        outputs = self.relation_model(**inputs)
                    
                    # 获取预测结果
                    prediction = outputs.logits.argmax(dim=1)[0].item()
                    pred_relation = self.id2relation[prediction]
                    
                    # 如果预测为有关系
                    if pred_relation != "无关系":
                        relations.append({
                            "head": head,
                            "tail": tail,
                            "type": pred_relation
                        })
        
        return relations

def main(args):
    evaluator = ModelEvaluator(args.ner_model_path, args.relation_model_path)
    
    if args.ner_test_file:
        evaluator.evaluate_ner(args.ner_test_file)
    
    if args.relation_test_file:
        evaluator.evaluate_relation(args.relation_test_file)
    
    if args.doc_path:
        evaluator.evaluate_on_document(args.doc_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="评估NER和关系抽取模型")
    parser.add_argument("--ner_model_path", type=str, default="models/ner", help="NER模型路径")
    parser.add_argument("--relation_model_path", type=str, default="models/relation", help="关系抽取模型路径")
    parser.add_argument("--ner_test_file", type=str, default="data/labeled_data/ner_test.json", help="NER测试数据文件")
    parser.add_argument("--relation_test_file", type=str, default="data/labeled_data/relation_test.json", help="关系抽取测试数据文件")
    parser.add_argument("--doc_path", type=str, help="要评估的文档路径")
    
    args = parser.parse_args()
    main(args) 