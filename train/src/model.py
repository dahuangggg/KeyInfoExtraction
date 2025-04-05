import torch
import torch.nn as nn
from torch.nn import CrossEntropyLoss
from transformers import BertModel, BertPreTrainedModel
from TorchCRF import CRF

class BertCRF(BertPreTrainedModel):
    """BERT与CRF结合的序列标注模型"""
    
    def __init__(self, config, num_labels):
        super(BertCRF, self).__init__(config)
        self.num_labels = num_labels
        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.classifier = nn.Linear(config.hidden_size, num_labels)
        self.crf = CRF(num_labels, batch_first=True)
        
        # 初始化权重
        self.init_weights()
    
    def forward(self, input_ids, token_type_ids=None, attention_mask=None, labels=None):
        """
        Args:
            input_ids: 输入token IDs
            token_type_ids: token类型IDs
            attention_mask: 注意力掩码
            labels: 标签序列
        
        Returns:
            loss: 如果提供labels，返回损失值
            emissions: 模型输出的发射分数
            tags: 预测的标签序列
        """
        # BERT编码
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        
        sequence_output = outputs[0]
        sequence_output = self.dropout(sequence_output)
        emissions = self.classifier(sequence_output)
        
        if labels is not None:
            # 计算CRF损失
            mask = attention_mask.byte()
            loss = -1 * self.crf(emissions, labels, mask=mask, reduction='mean')
            return loss, emissions
        else:
            # 预测标签序列
            mask = attention_mask.byte()
            tags = self.crf.decode(emissions, mask=mask)
            return emissions, tags


class HierarchicalBertCRF(nn.Module):
    """
    层次分类BERT+CRF模型
    先识别物理状态组，再基于物理状态组识别物理状态和试验项目
    """
    
    def __init__(self, level1_model, level2_model):
        """
        Args:
            level1_model: 一级模型，用于识别物理状态组
            level2_model: 二级模型，用于识别物理状态和试验项目
        """
        super(HierarchicalBertCRF, self).__init__()
        self.level1_model = level1_model
        self.level2_model = level2_model
    
    def forward(self, input_ids, token_type_ids=None, attention_mask=None, level1_labels=None, level2_labels=None):
        """
        前向传播，先进行一级分类，再基于一级分类结果进行二级分类
        
        Args:
            input_ids: 输入token IDs
            token_type_ids: token类型IDs
            attention_mask: 注意力掩码
            level1_labels: 一级标签序列
            level2_labels: 二级标签序列
        
        Returns:
            loss: 如果提供labels，返回损失值
            (level1_emissions, level2_emissions): 模型输出的发射分数
            (level1_tags, level2_tags): 预测的标签序列
        """
        # 一级分类（物理状态组）
        if level1_labels is not None and level2_labels is not None:
            # 训练模式
            level1_loss, level1_emissions = self.level1_model(
                input_ids=input_ids,
                token_type_ids=token_type_ids,
                attention_mask=attention_mask,
                labels=level1_labels
            )
            
            # 二级分类（物理状态和试验项目）
            level2_loss, level2_emissions = self.level2_model(
                input_ids=input_ids,
                token_type_ids=token_type_ids,
                attention_mask=attention_mask,
                labels=level2_labels
            )
            
            # 总损失为两级分类损失之和，可以添加权重
            total_loss = level1_loss + level2_loss
            return total_loss, (level1_emissions, level2_emissions)
        
        else:
            # 预测模式
            level1_emissions, level1_tags = self.level1_model(
                input_ids=input_ids,
                token_type_ids=token_type_ids,
                attention_mask=attention_mask
            )
            
            # 基于一级预测结果，增强二级预测
            # 这里可以实现更复杂的逻辑，将一级预测结果作为特征输入二级模型
            level2_emissions, level2_tags = self.level2_model(
                input_ids=input_ids,
                token_type_ids=token_type_ids,
                attention_mask=attention_mask
            )
            
            return (level1_emissions, level2_emissions), (level1_tags, level2_tags)


class EnhancedHierarchicalBertCRF(nn.Module):
    """
    增强版层次分类模型，将一级预测结果作为二级模型的输入特征
    """
    
    def __init__(self, config, level1_num_labels, level2_num_labels):
        """
        Args:
            config: BERT配置
            level1_num_labels: 一级标签数量
            level2_num_labels: 二级标签数量
        """
        super(EnhancedHierarchicalBertCRF, self).__init__()
        
        # 共享BERT层
        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        
        # 一级分类器
        self.level1_classifier = nn.Linear(config.hidden_size, level1_num_labels)
        self.level1_crf = CRF(level1_num_labels, batch_first=True)
        
        # 二级分类器（包含一级预测结果作为输入）
        self.level2_classifier = nn.Linear(config.hidden_size + level1_num_labels, level2_num_labels)
        self.level2_crf = CRF(level2_num_labels, batch_first=True)
    
    def forward(self, input_ids, token_type_ids=None, attention_mask=None, level1_labels=None, level2_labels=None):
        """
        前向传播
        
        Args:
            input_ids: 输入token IDs
            token_type_ids: token类型IDs
            attention_mask: 注意力掩码
            level1_labels: 一级标签序列
            level2_labels: 二级标签序列
        
        Returns:
            loss: 如果提供labels，返回损失值
            (level1_emissions, level2_emissions): 模型输出的发射分数
            (level1_tags, level2_tags): 预测的标签序列
        """
        # BERT编码
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        
        sequence_output = outputs[0]
        sequence_output = self.dropout(sequence_output)
        
        # 一级分类
        level1_emissions = self.level1_classifier(sequence_output)
        
        # 获取一级预测结果
        if level1_labels is not None:
            # 训练模式，使用真实标签
            batch_size, seq_len = level1_labels.size()
            level1_one_hot = torch.zeros(batch_size, seq_len, self.level1_classifier.out_features, device=input_ids.device)
            level1_one_hot.scatter_(2, level1_labels.unsqueeze(2), 1)
        else:
            # 预测模式，使用模型预测
            mask = attention_mask.byte()
            level1_tags = self.level1_crf.decode(level1_emissions, mask=mask)
            
            # 将预测标签转换为one-hot向量
            batch_size, seq_len = input_ids.size()
            level1_one_hot = torch.zeros(batch_size, seq_len, self.level1_classifier.out_features, device=input_ids.device)
            
            for i, tags in enumerate(level1_tags):
                for j, tag in enumerate(tags):
                    if j < seq_len:
                        level1_one_hot[i, j, tag] = 1
        
        # 拼接BERT输出和一级预测结果
        enhanced_features = torch.cat([sequence_output, level1_one_hot], dim=2)
        
        # 二级分类
        level2_emissions = self.level2_classifier(enhanced_features)
        
        if level1_labels is not None and level2_labels is not None:
            # 计算一级损失
            mask = attention_mask.byte()
            level1_loss = -1 * self.level1_crf(level1_emissions, level1_labels, mask=mask, reduction='mean')
            
            # 计算二级损失
            level2_loss = -1 * self.level2_crf(level2_emissions, level2_labels, mask=mask, reduction='mean')
            
            # 总损失
            total_loss = level1_loss + level2_loss
            return total_loss, (level1_emissions, level2_emissions)
        else:
            # 预测二级标签
            mask = attention_mask.byte()
            level2_tags = self.level2_crf.decode(level2_emissions, mask=mask)
            
            return (level1_emissions, level2_emissions), (level1_tags, level2_tags)