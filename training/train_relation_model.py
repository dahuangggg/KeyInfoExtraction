import os
import json
import argparse
import numpy as np
from tqdm import tqdm
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from transformers import TrainingArguments, Trainer
from transformers import get_linear_schedule_with_warmup
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report

# 设置随机种子
def set_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)

# 关系抽取数据集类
class RelationDataset(Dataset):
    def __init__(self, data, tokenizer, relation2id, max_length=512):
        self.data = data
        self.tokenizer = tokenizer
        self.relation2id = relation2id
        self.max_length = max_length
        self.examples = self._create_examples()
    
    def _create_examples(self):
        examples = []
        for item in self.data:
            text = item["text"]
            relations = item["relations"]
            
            for relation in relations:
                head = relation["head"]
                tail = relation["tail"]
                relation_type = relation["type"]
                
                # 标记头尾实体
                marked_text = text.replace(head, f"[HEAD]{head}[/HEAD]", 1)
                marked_text = marked_text.replace(tail, f"[TAIL]{tail}[/TAIL]", 1)
                
                examples.append({
                    "text": marked_text,
                    "relation": relation_type
                })
                
            # 添加一些负样本（无关系）
            if len(relations) > 0:
                # 随机选择文本中的两个词作为头尾实体
                words = text.split()
                if len(words) >= 4:
                    for _ in range(min(len(relations), 2)):  # 添加与正样本数量相当的负样本
                        idx1, idx2 = np.random.choice(len(words), 2, replace=False)
                        head = words[idx1]
                        tail = words[idx2]
                        
                        # 检查这对实体是否已经有关系
                        has_relation = False
                        for relation in relations:
                            if relation["head"] == head and relation["tail"] == tail:
                                has_relation = True
                                break
                        
                        if not has_relation:
                            marked_text = text.replace(head, f"[HEAD]{head}[/HEAD]", 1)
                            marked_text = marked_text.replace(tail, f"[TAIL]{tail}[/TAIL]", 1)
                            
                            examples.append({
                                "text": marked_text,
                                "relation": "无关系"
                            })
        
        return examples
    
    def __len__(self):
        return len(self.examples)
    
    def __getitem__(self, idx):
        example = self.examples[idx]
        text = example["text"]
        relation = example["relation"]
        
        # 转换为模型输入格式
        inputs = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        # 返回模型输入
        return {
            "input_ids": inputs["input_ids"][0],
            "attention_mask": inputs["attention_mask"][0],
            "labels": torch.tensor(self.relation2id[relation])
        }

# 评估函数
def compute_metrics(pred):
    predictions, labels = pred
    predictions = np.argmax(predictions, axis=1)
    
    # 计算指标
    precision, recall, f1, _ = precision_recall_fscore_support(labels, predictions, average='weighted')
    acc = accuracy_score(labels, predictions)
    
    return {
        "accuracy": acc,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

def main(args):
    # 设置随机种子
    set_seed(args.seed)
    
    # 加载数据
    with open(args.train_file, 'r', encoding='utf-8') as f:
        train_data = json.load(f)
    
    with open(args.dev_file, 'r', encoding='utf-8') as f:
        dev_data = json.load(f)
    
    # 构建关系类型映射
    relations = ["无关系"]  # 添加无关系类型
    for item in train_data:
        for relation in item["relations"]:
            relation_type = relation["type"]
            if relation_type not in relations:
                relations.append(relation_type)
    
    relation2id = {relation: i for i, relation in enumerate(relations)}
    id2relation = {i: relation for i, relation in enumerate(relations)}
    
    # 保存关系类型映射
    with open(os.path.join(args.output_dir, "relation2id.json"), 'w', encoding='utf-8') as f:
        json.dump(relation2id, f, ensure_ascii=False, indent=2)
    
    # 加载分词器和模型
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path)
    
    # 添加特殊标记
    special_tokens = {"additional_special_tokens": ["[HEAD]", "[/HEAD]", "[TAIL]", "[/TAIL]"]}
    tokenizer.add_special_tokens(special_tokens)
    
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name_or_path,
        num_labels=len(relations)
    )
    
    # 调整模型以适应新的词汇表大小
    model.resize_token_embeddings(len(tokenizer))
    
    # 创建数据集
    train_dataset = RelationDataset(train_data, tokenizer, relation2id, args.max_length)
    dev_dataset = RelationDataset(dev_data, tokenizer, relation2id, args.max_length)
    
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
        compute_metrics=compute_metrics
    )
    
    # 训练模型
    print("开始训练关系抽取模型...")
    trainer.train()
    
    # 评估模型
    print("评估模型...")
    eval_results = trainer.evaluate()
    print(f"评估结果: {eval_results}")
    
    # 保存模型
    print(f"保存模型到 {args.output_dir}")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    
    # 详细评估
    print("生成详细评估报告...")
    eval_dataloader = trainer.get_eval_dataloader()
    model.eval()
    
    all_preds = []
    all_labels = []
    
    for batch in tqdm(eval_dataloader, desc="评估"):
        batch = {k: v.to(trainer.args.device) for k, v in batch.items()}
        with torch.no_grad():
            outputs = model(**batch)
        
        predictions = outputs.logits.argmax(dim=-1).cpu().numpy()
        labels = batch["labels"].cpu().numpy()
        
        all_preds.extend(predictions)
        all_labels.extend(labels)
    
    # 打印分类报告
    target_names = [id2relation[i] for i in range(len(relations))]
    print(classification_report(all_labels, all_preds, target_names=target_names))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="训练关系抽取模型")
    parser.add_argument("--train_file", type=str, default="data/labeled_data/relation_train.json", help="训练数据文件")
    parser.add_argument("--dev_file", type=str, default="data/labeled_data/relation_dev.json", help="验证数据文件")
    parser.add_argument("--model_name_or_path", type=str, default="bert-base-chinese", help="预训练模型名称或路径")
    parser.add_argument("--output_dir", type=str, default="models/relation", help="输出目录")
    parser.add_argument("--max_length", type=int, default=512, help="最大序列长度")
    parser.add_argument("--batch_size", type=int, default=8, help="批次大小")
    parser.add_argument("--learning_rate", type=float, default=2e-5, help="学习率")
    parser.add_argument("--weight_decay", type=float, default=0.01, help="权重衰减")
    parser.add_argument("--epochs", type=int, default=3, help="训练轮数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    
    args = parser.parse_args()
    main(args) 