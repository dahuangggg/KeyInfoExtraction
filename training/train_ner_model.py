import os
import json
import argparse
import numpy as np
from tqdm import tqdm
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import TrainingArguments, Trainer, DataCollatorForTokenClassification
from transformers import get_linear_schedule_with_warmup
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from seqeval.metrics import f1_score, precision_score, recall_score

# 设置随机种子
def set_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)

# NER数据集类
class NERDataset(Dataset):
    def __init__(self, data, tokenizer, label2id, max_length=512):
        self.data = data
        self.tokenizer = tokenizer
        self.label2id = label2id
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        text = item["text"]
        entities = item["entities"]
        
        # 对文本进行分词
        tokens = self.tokenizer.tokenize(text)
        if len(tokens) > self.max_length - 2:  # 考虑[CLS]和[SEP]
            tokens = tokens[:self.max_length - 2]
        
        # 构建标签序列
        labels = ["O"] * len(tokens)
        
        # 将实体标签映射到分词后的位置
        for entity in entities:
            entity_text = entity["text"]
            entity_label = entity["label"]
            
            # 在分词后的文本中查找实体
            entity_tokens = self.tokenizer.tokenize(entity_text)
            if not entity_tokens:
                continue
                
            for i in range(len(tokens) - len(entity_tokens) + 1):
                if tokens[i:i+len(entity_tokens)] == entity_tokens:
                    # 使用BIO标注方式
                    labels[i] = f"B-{entity_label}"
                    for j in range(1, len(entity_tokens)):
                        labels[i+j] = f"I-{entity_label}"
        
        # 转换为模型输入格式
        inputs = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        # 添加标签ID
        label_ids = []
        label_ids.append(self.label2id["O"])  # [CLS]标签
        
        for label in labels:
            label_ids.append(self.label2id.get(label, self.label2id["O"]))
            
        label_ids.append(self.label2id["O"])  # [SEP]标签
        
        # 填充到最大长度
        if len(label_ids) < self.max_length:
            label_ids.extend([self.label2id["O"]] * (self.max_length - len(label_ids)))
        else:
            label_ids = label_ids[:self.max_length]
        
        # 返回模型输入
        return {
            "input_ids": inputs["input_ids"][0],
            "attention_mask": inputs["attention_mask"][0],
            "labels": torch.tensor(label_ids)
        }

# 评估函数
def compute_metrics(pred):
    predictions, labels = pred
    predictions = np.argmax(predictions, axis=2)
    
    # 移除填充标记
    true_predictions = [
        [id2label[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    true_labels = [
        [id2label[l] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    
    # 计算指标
    results = {
        "precision": precision_score(true_labels, true_predictions),
        "recall": recall_score(true_labels, true_predictions),
        "f1": f1_score(true_labels, true_predictions)
    }
    return results

def main(args):
    # 设置随机种子
    set_seed(args.seed)
    
    # 加载数据
    with open(args.train_file, 'r', encoding='utf-8') as f:
        train_data = json.load(f)
    
    with open(args.dev_file, 'r', encoding='utf-8') as f:
        dev_data = json.load(f)
    
    # 构建标签映射
    labels = ["O"]
    for item in train_data:
        for entity in item["entities"]:
            label = entity["label"]
            if f"B-{label}" not in labels:
                labels.append(f"B-{label}")
                labels.append(f"I-{label}")
    
    label2id = {label: i for i, label in enumerate(labels)}
    id2label = {i: label for i, label in enumerate(labels)}
    
    # 保存标签映射
    with open(os.path.join(args.output_dir, "label2id.json"), 'w', encoding='utf-8') as f:
        json.dump(label2id, f, ensure_ascii=False, indent=2)
    
    # 加载分词器和模型
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path)
    model = AutoModelForTokenClassification.from_pretrained(
        args.model_name_or_path,
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id
    )
    
    # 创建数据集
    train_dataset = NERDataset(train_data, tokenizer, label2id, args.max_length)
    dev_dataset = NERDataset(dev_data, tokenizer, label2id, args.max_length)
    
    # 数据收集器
    data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)
    
    # 训练参数
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        evaluation_strategy="epoch",
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        weight_decay=args.weight_decay,
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        report_to="none"
    )
    
    # 创建Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=dev_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics
    )
    
    # 训练模型
    print("开始训练NER模型...")
    trainer.train()
    
    # 评估模型
    print("评估模型...")
    eval_results = trainer.evaluate()
    print(f"评估结果: {eval_results}")
    
    # 保存模型
    print(f"保存模型到 {args.output_dir}")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="训练NER模型")
    parser.add_argument("--train_file", type=str, default="data/labeled_data/ner_train.json", help="训练数据文件")
    parser.add_argument("--dev_file", type=str, default="data/labeled_data/ner_dev.json", help="验证数据文件")
    parser.add_argument("--model_name_or_path", type=str, default="bert-base-chinese", help="预训练模型名称或路径")
    parser.add_argument("--output_dir", type=str, default="models/ner", help="输出目录")
    parser.add_argument("--max_length", type=int, default=512, help="最大序列长度")
    parser.add_argument("--batch_size", type=int, default=8, help="批次大小")
    parser.add_argument("--learning_rate", type=float, default=2e-5, help="学习率")
    parser.add_argument("--weight_decay", type=float, default=0.01, help="权重衰减")
    parser.add_argument("--epochs", type=int, default=3, help="训练轮数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    
    args = parser.parse_args()
    main(args) 