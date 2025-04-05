import torch
from torch.utils.data import Dataset, DataLoader
import json
import os
import numpy as np

class NERDataset(Dataset):
    """用于序列标注的数据集"""
    
    def __init__(self, texts, labels, tokenizer, max_length=512, label_map=None):
        """
        Args:
            texts: 文本列表
            labels: 标签列表，与texts长度相同
            tokenizer: BERT tokenizer
            max_length: 最大序列长度
            label_map: 标签映射，如果为None则自动构建
        """
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # 构建标签映射
        self.label_map = label_map if label_map else self._build_label_map(labels)
        self.id_to_label = {v: k for k, v in self.label_map.items()}
    
    def _build_label_map(self, labels):
        """构建标签到ID的映射"""
        unique_labels = set()
        for label_seq in labels:
            unique_labels.update(label_seq)
        
        label_map = {label: i for i, label in enumerate(sorted(unique_labels))}
        return label_map
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        
        # BERT tokenization会引入子词，需要对齐标签
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # 获取子词到原始词的映射
        word_ids = encoding.word_ids()
        
        # 初始化标签序列
        label_ids = torch.ones(self.max_length, dtype=torch.long) * -100  # 忽略的标签用-100表示
        
        # 通过word_ids对齐标签
        previous_word_id = None
        
        for i, word_id in enumerate(word_ids):
            # 特殊token (CLS, SEP, PAD)
            if word_id is None:
                label_ids[i] = -100
            # 第一个子词使用原始标签
            elif word_id != previous_word_id:
                label_ids[i] = self.label_map.get(label[word_id], 0)  # 默认为O标签
            # 非第一个子词继承前一个标签
            else:
                # 处理BIO标签
                prev_label = self.id_to_label.get(label_ids[i-1].item(), 'O')
                if prev_label.startswith('B-'):
                    label_ids[i] = self.label_map.get(f'I-{prev_label[2:]}', 0)
                else:
                    label_ids[i] = label_ids[i-1]
            
            previous_word_id = word_id
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'token_type_ids': encoding['token_type_ids'].squeeze(),
            'labels': label_ids
        }


class HierarchicalNERDataset(Dataset):
    """层次结构的命名实体识别数据集"""
    
    def __init__(self, texts, level1_labels, level2_labels, tokenizer, max_length=512, level1_label_map=None, level2_label_map=None):
        """
        Args:
            texts: 文本列表
            level1_labels: 一级标签列表（物理状态组）
            level2_labels: 二级标签列表（物理状态和试验项目）
            tokenizer: BERT tokenizer
            max_length: 最大序列长度
            level1_label_map: 一级标签映射
            level2_label_map: 二级标签映射
        """
        self.texts = texts
        self.level1_labels = level1_labels
        self.level2_labels = level2_labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # 构建标签映射
        self.level1_label_map = level1_label_map if level1_label_map else self._build_label_map(level1_labels)
        self.level2_label_map = level2_label_map if level2_label_map else self._build_label_map(level2_labels)
        
        self.id_to_level1_label = {v: k for k, v in self.level1_label_map.items()}
        self.id_to_level2_label = {v: k for k, v in self.level2_label_map.items()}
    
    def _build_label_map(self, labels):
        """构建标签到ID的映射"""
        unique_labels = set()
        for label_seq in labels:
            unique_labels.update(label_seq)
        
        label_map = {label: i for i, label in enumerate(sorted(unique_labels))}
        return label_map
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = self.texts[idx]
        level1_label = self.level1_labels[idx]
        level2_label = self.level2_labels[idx]
        
        # BERT tokenization会引入子词，需要对齐标签
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # 获取子词到原始词的映射
        word_ids = encoding.word_ids()
        
        # 初始化标签序列
        level1_label_ids = torch.ones(self.max_length, dtype=torch.long) * -100
        level2_label_ids = torch.ones(self.max_length, dtype=torch.long) * -100
        
        # 通过word_ids对齐标签
        previous_word_id = None
        
        for i, word_id in enumerate(word_ids):
            # 特殊token (CLS, SEP, PAD)
            if word_id is None:
                level1_label_ids[i] = -100
                level2_label_ids[i] = -100
            # 第一个子词使用原始标签
            elif word_id != previous_word_id:
                level1_label_ids[i] = self.level1_label_map.get(level1_label[word_id], 0)
                level2_label_ids[i] = self.level2_label_map.get(level2_label[word_id], 0)
            # 非第一个子词继承前一个标签
            else:
                # 处理BIO标签
                prev_level1_label = self.id_to_level1_label.get(level1_label_ids[i-1].item(), 'O')
                if prev_level1_label.startswith('B-'):
                    level1_label_ids[i] = self.level1_label_map.get(f'I-{prev_level1_label[2:]}', 0)
                else:
                    level1_label_ids[i] = level1_label_ids[i-1]
                
                prev_level2_label = self.id_to_level2_label.get(level2_label_ids[i-1].item(), 'O')
                if prev_level2_label.startswith('B-'):
                    level2_label_ids[i] = self.level2_label_map.get(f'I-{prev_level2_label[2:]}', 0)
                else:
                    level2_label_ids[i] = level2_label_ids[i-1]
            
            previous_word_id = word_id
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'token_type_ids': encoding['token_type_ids'].squeeze(),
            'level1_labels': level1_label_ids,
            'level2_labels': level2_label_ids
        }


def prepare_data_loaders(train_data, val_data, test_data, tokenizer, batch_size=16, max_length=512):
    """
    准备训练、验证和测试数据加载器
    
    Args:
        train_data: 训练数据
        val_data: 验证数据
        test_data: 测试数据
        tokenizer: BERT tokenizer
        batch_size: 批处理大小
        max_length: 最大序列长度
    
    Returns:
        训练、验证和测试数据加载器
    """
    # 提取文本和标签
    train_texts = [item['text'] for item in train_data]
    train_labels = [item['labels'] for item in train_data]
    
    val_texts = [item['text'] for item in val_data]
    val_labels = [item['labels'] for item in val_data]
    
    test_texts = [item['text'] for item in test_data]
    test_labels = [item['labels'] for item in test_data]
    
    # 创建数据集
    train_dataset = NERDataset(train_texts, train_labels, tokenizer, max_length)
    
    # 使用训练集的标签映射
    val_dataset = NERDataset(val_texts, val_labels, tokenizer, max_length, train_dataset.label_map)
    test_dataset = NERDataset(test_texts, test_labels, tokenizer, max_length, train_dataset.label_map)
    
    # 创建数据加载器
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    return train_loader, val_loader, test_loader, train_dataset.label_map


def prepare_hierarchical_data_loaders(train_data, val_data, test_data, tokenizer, batch_size=16, max_length=512):
    """
    准备层次结构的训练、验证和测试数据加载器
    
    Args:
        train_data: 训练数据
        val_data: 验证数据
        test_data: 测试数据
        tokenizer: BERT tokenizer
        batch_size: 批处理大小
        max_length: 最大序列长度
    
    Returns:
        训练、验证和测试数据加载器，以及标签映射
    """
    # 提取文本和标签
    train_texts = [item['text'] for item in train_data]
    train_level1_labels = [item['level1_labels'] for item in train_data]
    train_level2_labels = [item['level2_labels'] for item in train_data]
    
    val_texts = [item['text'] for item in val_data]
    val_level1_labels = [item['level1_labels'] for item in val_data]
    val_level2_labels = [item['level2_labels'] for item in val_data]
    
    test_texts = [item['text'] for item in test_data]
    test_level1_labels = [item['level1_labels'] for item in test_data]
    test_level2_labels = [item['level2_labels'] for item in test_data]
    
    # 创建数据集
    train_dataset = HierarchicalNERDataset(
        train_texts, train_level1_labels, train_level2_labels, tokenizer, max_length
    )
    
    # 使用训练集的标签映射
    val_dataset = HierarchicalNERDataset(
        val_texts, val_level1_labels, val_level2_labels, tokenizer, max_length,
        train_dataset.level1_label_map, train_dataset.level2_label_map
    )
    
    test_dataset = HierarchicalNERDataset(
        test_texts, test_level1_labels, test_level2_labels, tokenizer, max_length,
        train_dataset.level1_label_map, train_dataset.level2_label_map
    )
    
    # 创建数据加载器
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    return (
        train_loader, val_loader, test_loader,
        train_dataset.level1_label_map, train_dataset.level2_label_map
    )


def load_training_data(data_dir, split=True, split_ratio=(0.8, 0.1, 0.1), seed=42):
    """
    加载训练数据
    
    Args:
        data_dir: 训练数据目录
        split: 是否划分数据集
        split_ratio: 训练、验证和测试集的比例
        seed: 随机种子
    
    Returns:
        如果split=True，返回训练、验证和测试数据
        否则返回所有数据
    """
    all_data = []
    
    # 遍历目录加载所有训练数据
    for file in os.listdir(data_dir):
        if file.endswith('_training.json'):
            with open(os.path.join(data_dir, file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.extend(data)
    
    # 如果不划分，直接返回所有数据
    if not split:
        return all_data
    
    # 设置随机种子
    np.random.seed(seed)
    np.random.shuffle(all_data)
    
    # 计算划分点
    n = len(all_data)
    train_end = int(n * split_ratio[0])
    val_end = train_end + int(n * split_ratio[1])
    
    # 划分数据集
    train_data = all_data[:train_end]
    val_data = all_data[train_end:val_end]
    test_data = all_data[val_end:]
    
    return train_data, val_data, test_data


def load_hierarchical_training_data(data_dir, split=True, split_ratio=(0.8, 0.1, 0.1), seed=42):
    """
    加载层次结构的训练数据
    
    Args:
        data_dir: 训练数据目录
        split: 是否划分数据集
        split_ratio: 训练、验证和测试集的比例
        seed: 随机种子
    
    Returns:
        如果split=True，返回训练、验证和测试数据
        否则返回所有数据
    """
    # 加载层次格式的训练数据
    hierarchical_data_path = os.path.join(data_dir, "hierarchical_training_data.json")
    
    if not os.path.exists(hierarchical_data_path):
        raise FileNotFoundError(f"层次训练数据文件不存在: {hierarchical_data_path}")
    
    with open(hierarchical_data_path, 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    # 如果不划分，直接返回所有数据
    if not split:
        return all_data
    
    # 设置随机种子
    np.random.seed(seed)
    np.random.shuffle(all_data)
    
    # 计算划分点
    n = len(all_data)
    train_end = int(n * split_ratio[0])
    val_end = train_end + int(n * split_ratio[1])
    
    # 划分数据集
    train_data = all_data[:train_end]
    val_data = all_data[train_end:val_end]
    test_data = all_data[val_end:]
    
    return train_data, val_data, test_data