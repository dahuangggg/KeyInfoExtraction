import torch
import numpy as np
from tqdm import tqdm
from transformers import AdamW, get_linear_schedule_with_warmup
from sklearn.metrics import precision_recall_fscore_support, classification_report
import matplotlib.pyplot as plt
import os
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def set_seed(seed):
    """设置随机种子"""
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    import random
    random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def train_bert_crf(model, train_loader, val_loader, device, epochs=3, lr=2e-5, output_dir=None, early_stopping=5):
    """
    训练BERT+CRF模型
    
    Args:
        model: 模型
        train_loader: 训练数据加载器
        val_loader: 验证数据加载器
        device: 设备（CPU或GPU）
        epochs: 训练轮数
        lr: 学习率
        output_dir: 输出目录，用于保存模型和训练日志
        early_stopping: 提前停止的轮数
    
    Returns:
        训练好的模型
    """
    # 创建输出目录
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 优化器
    no_decay = ['bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {
            'params': [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
            'weight_decay': 0.01
        },
        {
            'params': [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
            'weight_decay': 0.0
        }
    ]
    optimizer = AdamW(optimizer_grouped_parameters, lr=lr)
    
    # 学习率调度器
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.1 * total_steps),
        num_training_steps=total_steps
    )
    
    # 移动模型到设备
    model.to(device)
    
    # 训练循环
    best_f1 = 0.0
    no_improve_count = 0
    train_losses = []
    val_metrics = []
    
    for epoch in range(epochs):
        logger.info(f"Epoch {epoch+1}/{epochs}")
        
        # 训练模式
        model.train()
        train_loss = 0.0
        
        # 进度条
        progress_bar = tqdm(train_loader, desc=f"Training Epoch {epoch+1}")
        
        for batch in progress_bar:
            # 移动数据到设备
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            token_type_ids = batch['token_type_ids'].to(device)
            labels = batch['labels'].to(device)
            
            # 前向传播
            optimizer.zero_grad()
            loss, _ = model(
                input_ids=input_ids,
                token_type_ids=token_type_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            
            # 反向传播
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            
            # 累计损失
            train_loss += loss.item()
            
            # 更新进度条
            progress_bar.set_postfix({"loss": loss.item()})
        
        # 计算平均训练损失
        avg_train_loss = train_loss / len(train_loader)
        train_losses.append(avg_train_loss)
        logger.info(f"Average training loss: {avg_train_loss:.4f}")
        
        # 验证
        metrics = evaluate_bert_crf(model, val_loader, device)
        val_metrics.append(metrics)
        logger.info(f"Validation metrics: {metrics}")
        
        # 检查是否是最佳模型
        if metrics['f1'] > best_f1:
            best_f1 = metrics['f1']
            no_improve_count = 0
            
            # 保存最佳模型
            if output_dir:
                model_path = os.path.join(output_dir, "best_model.pt")
                torch.save(model.state_dict(), model_path)
                logger.info(f"Saved best model to {model_path}")
        else:
            no_improve_count += 1
            logger.info(f"No improvement for {no_improve_count} epochs")
        
        # 提前停止
        if no_improve_count >= early_stopping:
            logger.info(f"Early stopping after {epoch+1} epochs")
            break
    
    # 绘制训练过程
    if output_dir:
        plot_training_process(train_losses, val_metrics, output_dir)
    
    # 加载最佳模型
    if output_dir:
        model.load_state_dict(torch.load(os.path.join(output_dir, "best_model.pt")))
    
    return model

def evaluate_bert_crf(model, data_loader, device, id_to_label=None):
    """
    评估BERT+CRF模型
    
    Args:
        model: 模型
        data_loader: 数据加载器
        device: 设备（CPU或GPU）
        id_to_label: ID到标签的映射
    
    Returns:
        评估指标字典
    """
    # 评估模式
    model.eval()
    
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for batch in tqdm(data_loader, desc="Evaluating"):
            # 移动数据到设备
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            token_type_ids = batch['token_type_ids'].to(device)
            labels = batch['labels'].to(device)
            
            # 前向传播
            _, pred_tags = model(
                input_ids=input_ids,
                token_type_ids=token_type_ids,
                attention_mask=attention_mask
            )
            
            # 处理预测结果和真实标签
            for i, (pred, label) in enumerate(zip(pred_tags, labels)):
                pred_list = pred
                label_list = label.cpu().numpy()
                mask = attention_mask[i].cpu().numpy()
                
                # 过滤掉padding和特殊token（-100）
                valid_indices = np.where((mask == 1) & (label_list != -100))[0]
                
                all_preds.extend([pred_list[j] for j in valid_indices])
                all_labels.extend([label_list[j] for j in valid_indices])
    
    # 转换ID到标签
    if id_to_label:
        all_preds = [id_to_label[p] for p in all_preds]
        all_labels = [id_to_label[l] for l in all_labels]
    
    # 计算指标
    precision, recall, f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average='weighted'
    )
    
    # 计算分类报告
    report = classification_report(all_labels, all_preds, digits=4)
    
    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'report': report
    }

def train_hierarchical_model(model, train_loader, val_loader, device, epochs=3, lr=2e-5, output_dir=None, early_stopping=5):
    """
    训练层次模型
    
    Args:
        model: 层次模型
        train_loader: 训练数据加载器
        val_loader: 验证数据加载器
        device: 设备（CPU或GPU）
        epochs: 训练轮数
        lr: 学习率
        output_dir: 输出目录
        early_stopping: 提前停止的轮数
    
    Returns:
        训练好的模型
    """
    # 创建输出目录
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 优化器
    no_decay = ['bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {
            'params': [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
            'weight_decay': 0.01
        },
        {
            'params': [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
            'weight_decay': 0.0
        }
    ]
    optimizer = AdamW(optimizer_grouped_parameters, lr=lr)
    
    # 学习率调度器
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.1 * total_steps),
        num_training_steps=total_steps
    )
    
    # 移动模型到设备
    model.to(device)
    
    # 训练循环
    best_f1 = 0.0
    no_improve_count = 0
    train_losses = []
    val_metrics = []
    
    for epoch in range(epochs):
        logger.info(f"Epoch {epoch+1}/{epochs}")
        
        # 训练模式
        model.train()
        train_loss = 0.0
        
        # 进度条
        progress_bar = tqdm(train_loader, desc=f"Training Epoch {epoch+1}")
        
        for batch in progress_bar:
            # 移动数据到设备
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            token_type_ids = batch['token_type_ids'].to(device)
            level1_labels = batch['level1_labels'].to(device)
            level2_labels = batch['level2_labels'].to(device)
            
            # 前向传播
            optimizer.zero_grad()
            loss, _ = model(
                input_ids=input_ids,
                token_type_ids=token_type_ids,
                attention_mask=attention_mask,
                level1_labels=level1_labels,
                level2_labels=level2_labels
            )
            
            # 反向传播
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            
            # 累计损失
            train_loss += loss.item()
            
            # 更新进度条
            progress_bar.set_postfix({"loss": loss.item()})
        
        # 计算平均训练损失
        avg_train_loss = train_loss / len(train_loader)
        train_losses.append(avg_train_loss)
        logger.info(f"Average training loss: {avg_train_loss:.4f}")
        
        # 验证
        metrics = evaluate_hierarchical_model(model, val_loader, device)
        val_metrics.append(metrics)
        logger.info(f"Validation metrics: {metrics}")
        
        # 检查是否是最佳模型
        if metrics['overall_f1'] > best_f1:
            best_f1 = metrics['overall_f1']
            no_improve_count = 0
            
            # 保存最佳模型
            if output_dir:
                model_path = os.path.join(output_dir, "best_hierarchical_model.pt")
                torch.save(model.state_dict(), model_path)
                logger.info(f"Saved best model to {model_path}")
        else:
            no_improve_count += 1
            logger.info(f"No improvement for {no_improve_count} epochs")
        
        # 提前停止
        if no_improve_count >= early_stopping:
            logger.info(f"Early stopping after {epoch+1} epochs")
            break
    
    # 绘制训练过程
    if output_dir:
        plot_hierarchical_training_process(train_losses, val_metrics, output_dir)
    
    # 加载最佳模型
    if output_dir:
        model.load_state_dict(torch.load(os.path.join(output_dir, "best_hierarchical_model.pt")))
    
    return model

def evaluate_hierarchical_model(model, data_loader, device, level1_id_to_label=None, level2_id_to_label=None):
    """
    评估层次模型
    
    Args:
        model: 层次模型
        data_loader: 数据加载器
        device: 设备（CPU或GPU）
        level1_id_to_label: 一级ID到标签的映射
        level2_id_to_label: 二级ID到标签的映射
    
    Returns:
        评估指标字典
    """
    # 评估模式
    model.eval()
    
    level1_preds = []
    level1_labels = []
    level2_preds = []
    level2_labels = []
    
    with torch.no_grad():
        for batch in tqdm(data_loader, desc="Evaluating"):
            # 移动数据到设备
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            token_type_ids = batch['token_type_ids'].to(device)
            level1_true = batch['level1_labels'].to(device)
            level2_true = batch['level2_labels'].to(device)
            
            # 前向传播
            _, (level1_tags, level2_tags) = model(
                input_ids=input_ids,
                token_type_ids=token_type_ids,
                attention_mask=attention_mask
            )
            
            # 处理预测结果和真实标签
            for i, (level1_pred, level1_label, level2_pred, level2_label) in enumerate(
                zip(level1_tags, level1_true, level2_tags, level2_true)
            ):
                mask = attention_mask[i].cpu().numpy()
                level1_label_np = level1_label.cpu().numpy()
                level2_label_np = level2_label.cpu().numpy()
                
                # 过滤掉padding和特殊token（-100）
                valid_indices = np.where((mask == 1) & (level1_label_np != -100) & (level2_label_np != -100))[0]
                
                level1_preds.extend([level1_pred[j] for j in valid_indices])
                level1_labels.extend([level1_label_np[j] for j in valid_indices])
                level2_preds.extend([level2_pred[j] for j in valid_indices])
                level2_labels.extend([level2_label_np[j] for j in valid_indices])
    
    # 转换ID到标签
    if level1_id_to_label:
        level1_preds = [level1_id_to_label[p] for p in level1_preds]
        level1_labels = [level1_id_to_label[l] for l in level1_labels]
    
    if level2_id_to_label:
        level2_preds = [level2_id_to_label[p] for p in level2_preds]
        level2_labels = [level2_id_to_label[l] for l in level2_labels]
    
    # 计算一级指标
    level1_precision, level1_recall, level1_f1, _ = precision_recall_fscore_support(
        level1_labels, level1_preds, average='weighted'
    )
    
    # 计算二级指标
    level2_precision, level2_recall, level2_f1, _ = precision_recall_fscore_support(
        level2_labels, level2_preds, average='weighted'
    )
    
    # 计算分类报告
    level1_report = classification_report(level1_labels, level1_preds, digits=4)
    level2_report = classification_report(level2_labels, level2_preds, digits=4)
    
    # 计算总体指标
    overall_precision = (level1_precision + level2_precision) / 2
    overall_recall = (level1_recall + level2_recall) / 2
    overall_f1 = (level1_f1 + level2_f1) / 2
    
    return {
        'level1': {
            'precision': level1_precision,
            'recall': level1_recall,
            'f1': level1_f1,
            'report': level1_report
        },
        'level2': {
            'precision': level2_precision,
            'recall': level2_recall,
            'f1': level2_f1,
            'report': level2_report
        },
        'overall_precision': overall_precision,
        'overall_recall': overall_recall,
        'overall_f1': overall_f1
    }

def plot_training_process(train_losses, val_metrics, output_dir):
    """
    绘制训练过程
    
    Args:
        train_losses: 训练损失列表
        val_metrics: 验证指标列表
        output_dir: 输出目录
    """
    # 创建图形
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # 绘制训练损失
    ax1.plot(train_losses, label='Training Loss')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training Loss')
    ax1.legend()
    
    # 绘制验证指标
    epochs = list(range(1, len(val_metrics) + 1))
    ax2.plot(epochs, [m['precision'] for m in val_metrics], label='Precision')
    ax2.plot(epochs, [m['recall'] for m in val_metrics], label='Recall')
    ax2.plot(epochs, [m['f1'] for m in val_metrics], label='F1')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Score')
    ax2.set_title('Validation Metrics')
    ax2.legend()
    
    # 保存图形
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'training_process.png'))
    plt.close()

def plot_hierarchical_training_process(train_losses, val_metrics, output_dir):
    """
    绘制层次模型的训练过程
    
    Args:
        train_losses: 训练损失列表
        val_metrics: 验证指标列表
        output_dir: 输出目录
    """
    # 创建图形
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))
    
    # 绘制训练损失
    ax1.plot(train_losses, label='Training Loss')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training Loss')
    ax1.legend()
    
    # 绘制一级验证指标
    epochs = list(range(1, len(val_metrics) + 1))
    ax2.plot(epochs, [m['level1']['precision'] for m in val_metrics], label='Precision')
    ax2.plot(epochs, [m['level1']['recall'] for m in val_metrics], label='Recall')
    ax2.plot(epochs, [m['level1']['f1'] for m in val_metrics], label='F1')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Score')
    ax2.set_title('Level 1 Validation Metrics')
    ax2.legend()
    
    # 绘制二级验证指标
    ax3.plot(epochs, [m['level2']['precision'] for m in val_metrics], label='Precision')
    ax3.plot(epochs, [m['level2']['recall'] for m in val_metrics], label='Recall')
    ax3.plot(epochs, [m['level2']['f1'] for m in val_metrics], label='F1')
    ax3.set_xlabel('Epoch')
    ax3.set_ylabel('Score')
    ax3.set_title('Level 2 Validation Metrics')
    ax3.legend()
    
    # 保存图形
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'hierarchical_training_process.png'))
    plt.close()

def predict(model, tokenizer, text, device, id_to_label, max_length=512):
    """
    使用模型进行预测
    
    Args:
        model: 模型
        tokenizer: tokenizer
        text: 待预测的文本
        device: 设备（CPU或GPU）
        id_to_label: ID到标签的映射
        max_length: 最大序列长度
    
    Returns:
        预测结果，格式为[(token, label), ...]
    """
    # 评估模式
    model.eval()
    
    # 对文本进行tokenize
    encoding = tokenizer(
        text,
        max_length=max_length,
        padding='max_length',
        truncation=True,
        return_tensors='pt'
    )
    
    # 移动数据到设备
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)
    token_type_ids = encoding['token_type_ids'].to(device)
    
    # 预测
    with torch.no_grad():
        _, pred_tags = model(
            input_ids=input_ids,
            token_type_ids=token_type_ids,
            attention_mask=attention_mask
        )
    
    # 获取子词到原始词的映射
    tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
    
    # 将预测结果与token对齐
    pred_labels = [id_to_label.get(tag_id, 'O') for tag_id in pred_tags[0]]
    
    # 过滤掉padding和特殊token
    valid_tokens = []
    valid_labels = []
    
    for i, (token, label) in enumerate(zip(tokens, pred_labels)):
        if token in [tokenizer.cls_token, tokenizer.sep_token, tokenizer.pad_token]:
            continue
        
        if attention_mask[0][i] == 0:
            continue
        
        valid_tokens.append(token)
        valid_labels.append(label)
    
    # 合并子词
    merged_result = []
    current_token = ""
    current_label = ""
    
    for token, label in zip(valid_tokens, valid_labels):
        if token.startswith("##"):
            current_token += token[2:]
        else:
            if current_token:
                merged_result.append((current_token, current_label))
            current_token = token
            current_label = label
    
    if current_token:
        merged_result.append((current_token, current_label))
    
    return merged_result

def hierarchical_predict(model, tokenizer, text, device, level1_id_to_label, level2_id_to_label, max_length=512):
    """
    使用层次模型进行预测
    
    Args:
        model: 层次模型
        tokenizer: tokenizer
        text: 待预测的文本
        device: 设备（CPU或GPU）
        level1_id_to_label: 一级ID到标签的映射
        level2_id_to_label: 二级ID到标签的映射
        max_length: 最大序列长度
    
    Returns:
        预测结果，格式为[(token, level1_label, level2_label), ...]
    """
    # 评估模式
    model.eval()
    
    # 对文本进行tokenize
    encoding = tokenizer(
        text,
        max_length=max_length,
        padding='max_length',
        truncation=True,
        return_tensors='pt'
    )
    
    # 移动数据到设备
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)
    token_type_ids = encoding['token_type_ids'].to(device)
    
    # 预测
    with torch.no_grad():
        _, (level1_tags, level2_tags) = model(
            input_ids=input_ids,
            token_type_ids=token_type_ids,
            attention_mask=attention_mask
        )
    
    # 获取子词到原始词的映射
    tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
    
    # 将预测结果与token对齐
    level1_labels = [level1_id_to_label.get(tag_id, 'O') for tag_id in level1_tags[0]]
    level2_labels = [level2_id_to_label.get(tag_id, 'O') for tag_id in level2_tags[0]]
    
    # 过滤掉padding和特殊token
    valid_tokens = []
    valid_level1_labels = []
    valid_level2_labels = []
    
    for i, (token, level1_label, level2_label) in enumerate(zip(tokens, level1_labels, level2_labels)):
        if token in [tokenizer.cls_token, tokenizer.sep_token, tokenizer.pad_token]:
            continue
        
        if attention_mask[0][i] == 0:
            continue
        
        valid_tokens.append(token)
        valid_level1_labels.append(level1_label)
        valid_level2_labels.append(level2_label)
    
    # 合并子词
    merged_result = []
    current_token = ""
    current_level1_label = ""
    current_level2_label = ""
    
    for token, level1_label, level2_label in zip(valid_tokens, valid_level1_labels, valid_level2_labels):
        if token.startswith("##"):
            current_token += token[2:]
        else:
            if current_token:
                merged_result.append((current_token, current_level1_label, current_level2_label))
            current_token = token
            current_level1_label = level1_label
            current_level2_label = level2_label
    
    if current_token:
        merged_result.append((current_token, current_level1_label, current_level2_label))
    
    return merged_result