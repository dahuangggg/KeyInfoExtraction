import os
import argparse
import json
import torch
import logging
from transformers import BertTokenizer, BertConfig
from sklearn.model_selection import train_test_split

# 导入自定义模块
from data_preprocessing import load_documents, clean_text, build_knowledge_base, preprocess_data
from annotation import create_annotation_tool, convert_to_training_data, convert_to_hierarchical_format
from model import BertCRF, HierarchicalBertCRF, EnhancedHierarchicalBertCRF
from data_processor import load_training_data, load_hierarchical_training_data, prepare_data_loaders, prepare_hierarchical_data_loaders
from training import set_seed, train_bert_crf, evaluate_bert_crf, train_hierarchical_model, evaluate_hierarchical_model, predict, hierarchical_predict

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ner_training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="训练NER模型用于电子元件文档信息提取")
    
    # 通用参数
    parser.add_argument("--mode", type=str, required=True, choices=["preprocess", "annotate", "train", "predict"], help="操作模式")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    
    # 数据预处理参数
    parser.add_argument("--data_dir", type=str, help="文档数据目录")
    parser.add_argument("--knowledge_base", type=str, help="知识库JSON文件路径")
    parser.add_argument("--output_dir", type=str, help="输出目录")
    
    # 标注参数
    parser.add_argument("--train_dir", type=str, help="训练数据目录")
    
    # 训练参数
    parser.add_argument("--model_type", type=str, default="hierarchical", choices=["simple", "hierarchical", "enhanced"], help="模型类型")
    parser.add_argument("--bert_model", type=str, default="bert-base-chinese", help="BERT模型")
    parser.add_argument("--max_length", type=int, default=512, help="最大序列长度")
    parser.add_argument("--batch_size", type=int, default=8, help="批处理大小")
    parser.add_argument("--learning_rate", type=float, default=2e-5, help="学习率")
    parser.add_argument("--epochs", type=int, default=5, help="训练轮数")
    parser.add_argument("--early_stopping", type=int, default=3, help="提前停止的轮数")
    
    # 预测参数
    parser.add_argument("--model_path", type=str, help="模型路径")
    parser.add_argument("--input_file", type=str, help="输入文件路径")
    parser.add_argument("--output_file", type=str, help="输出文件路径")
    
    return parser.parse_args()

def preprocess_mode(args):
    """预处理模式"""
    logger.info("运行预处理模式")
    
    # 检查参数
    if not args.data_dir or not args.knowledge_base or not args.output_dir:
        raise ValueError("预处理模式需要指定data_dir、knowledge_base和output_dir参数")
    
    # 加载文档
    logger.info(f"从 {args.data_dir} 加载文档")
    documents = load_documents(args.data_dir)
    logger.info(f"加载了 {len(documents)} 份文档")
    
    # 构建知识库
    logger.info(f"从 {args.knowledge_base} 构建知识库")
    knowledge_base = build_knowledge_base(args.knowledge_base)
    
    # 保存知识库
    os.makedirs(args.output_dir, exist_ok=True)
    kb_output_path = os.path.join(args.output_dir, "knowledge_base.json")
    with open(kb_output_path, 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=2)
    logger.info(f"知识库保存至 {kb_output_path}")
    
    # 预处理文档
    logger.info("预处理文档")
    preprocessed_docs = preprocess_data(documents, args.output_dir)
    logger.info(f"预处理完成，保存至 {args.output_dir}")
    
    return preprocessed_docs, knowledge_base

def annotate_mode(args):
    """标注模式"""
    logger.info("运行标注模式")
    
    # 检查参数
    if not args.data_dir or not args.knowledge_base or not args.output_dir:
        raise ValueError("标注模式需要指定data_dir、knowledge_base和output_dir参数")
    
    # 加载预处理后的文档
    logger.info(f"从 {args.data_dir} 加载预处理文档")
    documents = []
    for file in os.listdir(args.data_dir):
        if file.endswith('_preprocessed.json'):
            with open(os.path.join(args.data_dir, file), 'r', encoding='utf-8') as f:
                documents.append(json.load(f))
    logger.info(f"加载了 {len(documents)} 份预处理文档")
    
    # 加载知识库
    logger.info(f"从 {args.knowledge_base} 加载知识库")
    with open(args.knowledge_base, 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)
    
    # 自动标注
    logger.info("进行自动标注")
    annotation_dir = os.path.join(args.output_dir, "annotations")
    os.makedirs(annotation_dir, exist_ok=True)
    annotated_docs = create_annotation_tool(documents, knowledge_base, annotation_dir)
    logger.info(f"标注了 {len(annotated_docs)} 份文档，保存至 {annotation_dir}")
    
    # 转换为训练数据
    if args.train_dir:
        logger.info("转换为训练数据")
        training_dir = os.path.join(args.output_dir, "training")
        os.makedirs(training_dir, exist_ok=True)
        training_data = convert_to_training_data(annotated_docs, training_dir)
        logger.info(f"生成了 {len(training_data)} 条训练数据，保存至 {training_dir}")
        
        # 转换为层次格式
        logger.info("转换为层次格式")
        hierarchical_data = convert_to_hierarchical_format(training_data, training_dir)
        logger.info(f"生成了 {len(hierarchical_data)} 条层次格式的训练数据")
    
    return annotated_docs

def train_mode(args):
    """训练模式"""
    logger.info("运行训练模式")
    
    # 检查参数
    if not args.train_dir or not args.output_dir:
        raise ValueError("训练模式需要指定train_dir和output_dir参数")
    
    # 设置随机种子
    set_seed(args.seed)
    
    # 设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"使用设备: {device}")
    
    # 创建模型输出目录
    model_dir = os.path.join(args.output_dir, "models")
    os.makedirs(model_dir, exist_ok=True)
    
    # 加载tokenizer
    logger.info(f"加载tokenizer: {args.bert_model}")
    tokenizer = BertTokenizer.from_pretrained(args.bert_model)
    
    if args.model_type == "simple":
        # 加载训练数据
        logger.info("加载训练数据")
        train_data, val_data, test_data = load_training_data(args.train_dir)
        logger.info(f"加载了 {len(train_data)} 条训练数据, {len(val_data)} 条验证数据, {len(test_data)} 条测试数据")
        
        # 准备数据加载器
        logger.info("准备数据加载器")
        train_loader, val_loader, test_loader, label_map = prepare_data_loaders(
            train_data, val_data, test_data, tokenizer, batch_size=args.batch_size, max_length=args.max_length
        )
        
        # 保存标签映射
        label_map_path = os.path.join(model_dir, "label_map.json")
        with open(label_map_path, 'w', encoding='utf-8') as f:
            json.dump(label_map, f, ensure_ascii=False, indent=2)
        logger.info(f"标签映射保存至 {label_map_path}")
        
        # 反转标签映射
        id_to_label = {v: k for k, v in label_map.items()}
        
        # 初始化模型
        logger.info(f"初始化BERT+CRF模型，标签数量: {len(label_map)}")
        config = BertConfig.from_pretrained(args.bert_model)
        model = BertCRF.from_pretrained(args.bert_model, config=config, num_labels=len(label_map))
        
        # 训练模型
        logger.info("开始训练模型")
        model = train_bert_crf(
            model, train_loader, val_loader, device,
            epochs=args.epochs, lr=args.learning_rate,
            output_dir=model_dir, early_stopping=args.early_stopping
        )
        
        # 评估模型
        logger.info("在测试集上评估模型")
        test_metrics = evaluate_bert_crf(model, test_loader, device, id_to_label)
        logger.info(f"测试集评估指标: {test_metrics}")
        
        # 保存评估结果
        metrics_path = os.path.join(model_dir, "test_metrics.json")
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(test_metrics, f, ensure_ascii=False, indent=2)
        logger.info(f"测试指标保存至 {metrics_path}")
        
        # 保存tokenizer
        tokenizer.save_pretrained(os.path.join(model_dir, "tokenizer"))
        logger.info(f"Tokenizer保存至 {os.path.join(model_dir, 'tokenizer')}")
        
    elif args.model_type in ["hierarchical", "enhanced"]:
        # 加载层次训练数据
        logger.info("加载层次训练数据")
        train_data, val_data, test_data = load_hierarchical_training_data(args.train_dir)
        logger.info(f"加载了 {len(train_data)} 条层次训练数据, {len(val_data)} 条验证数据, {len(test_data)} 条测试数据")
        
        # 准备数据加载器
        logger.info("准备层次数据加载器")
        (
            train_loader, val_loader, test_loader,
            level1_label_map, level2_label_map
        ) = prepare_hierarchical_data_loaders(
            train_data, val_data, test_data, tokenizer, batch_size=args.batch_size, max_length=args.max_length
        )
        
        # 保存标签映射
        level1_label_map_path = os.path.join(model_dir, "level1_label_map.json")
        with open(level1_label_map_path, 'w', encoding='utf-8') as f:
            json.dump(level1_label_map, f, ensure_ascii=False, indent=2)
        
        level2_label_map_path = os.path.join(model_dir, "level2_label_map.json")
        with open(level2_label_map_path, 'w', encoding='utf-8') as f:
            json.dump(level2_label_map, f, ensure_ascii=False, indent=2)
        
        logger.info(f"标签映射保存至 {model_dir}")
        
        # 反转标签映射
        level1_id_to_label = {v: k for k, v in level1_label_map.items()}
        level2_id_to_label = {v: k for k, v in level2_label_map.items()}
        
        # 初始化模型
        logger.info(f"初始化层次模型，一级标签数量: {len(level1_label_map)}, 二级标签数量: {len(level2_label_map)}")
        config = BertConfig.from_pretrained(args.bert_model)
        
        if args.model_type == "hierarchical":
            # 初始化一级和二级分类器
            level1_model = BertCRF.from_pretrained(args.bert_model, config=config, num_labels=len(level1_label_map))
            level2_model = BertCRF.from_pretrained(args.bert_model, config=config, num_labels=len(level2_label_map))
            
            # 初始化层次模型
            model = HierarchicalBertCRF(level1_model, level2_model)
        else:  # enhanced
            model = EnhancedHierarchicalBertCRF(config, len(level1_label_map), len(level2_label_map))
        
        # 训练模型
        logger.info("开始训练层次模型")
        model = train_hierarchical_model(
            model, train_loader, val_loader, device,
            epochs=args.epochs, lr=args.learning_rate,
            output_dir=model_dir, early_stopping=args.early_stopping
        )
        
        # 评估模型
        logger.info("在测试集上评估层次模型")
        test_metrics = evaluate_hierarchical_model(
            model, test_loader, device, level1_id_to_label, level2_id_to_label
        )
        logger.info(f"测试集评估指标: {test_metrics}")
        
        # 保存评估结果
        metrics_path = os.path.join(model_dir, "hierarchical_test_metrics.json")
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(test_metrics, f, ensure_ascii=False, indent=2)
        logger.info(f"测试指标保存至 {metrics_path}")
        
        # 保存tokenizer
        tokenizer.save_pretrained(os.path.join(model_dir, "tokenizer"))
        logger.info(f"Tokenizer保存至 {os.path.join(model_dir, 'tokenizer')}")
    
    logger.info("训练完成!")

def predict_mode(args):
    """预测模式"""
    logger.info("运行预测模式")
    
    # 检查参数
    if not args.model_path or not args.input_file or not args.output_file:
        raise ValueError("预测模式需要指定model_path、input_file和output_file参数")
    
    # 加载文本
    logger.info(f"从 {args.input_file} 加载文本")
    with open(args.input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"使用设备: {device}")
    
    # 加载tokenizer
    tokenizer_path = os.path.join(args.model_path, "tokenizer")
    logger.info(f"加载tokenizer: {tokenizer_path}")
    tokenizer = BertTokenizer.from_pretrained(tokenizer_path)
    
    if args.model_type == "simple":
        # 加载标签映射
        label_map_path = os.path.join(args.model_path, "label_map.json")
        logger.info(f"加载标签映射: {label_map_path}")
        with open(label_map_path, 'r', encoding='utf-8') as f:
            label_map = json.load(f)
        
        # 反转标签映射
        id_to_label = {int(v): k for k, v in label_map.items()}
        
        # 加载模型
        model_config = BertConfig.from_pretrained(args.bert_model)
        model = BertCRF(model_config, num_labels=len(label_map))
        
        model_file = os.path.join(args.model_path, "best_model.pt")
        logger.info(f"加载模型: {model_file}")
        model.load_state_dict(torch.load(model_file, map_location=device))
        model.to(device)
        
        # 预测
        logger.info("开始预测")
        result = predict(model, tokenizer, text, device, id_to_label, max_length=args.max_length)
        
        # 格式化结果
        output = []
        for token, label in result:
            output.append({
                "token": token,
                "label": label
            })
        
    elif args.model_type in ["hierarchical", "enhanced"]:
        # 加载标签映射
        level1_label_map_path = os.path.join(args.model_path, "level1_label_map.json")
        level2_label_map_path = os.path.join(args.model_path, "level2_label_map.json")
        
        logger.info(f"加载标签映射: {level1_label_map_path}, {level2_label_map_path}")
        
        with open(level1_label_map_path, 'r', encoding='utf-8') as f:
            level1_label_map = json.load(f)
        
        with open(level2_label_map_path, 'r', encoding='utf-8') as f:
            level2_label_map = json.load(f)
        
        # 反转标签映射
        level1_id_to_label = {int(v): k for k, v in level1_label_map.items()}
        level2_id_to_label = {int(v): k for k, v in level2_label_map.items()}
        
        # 加载模型
        model_config = BertConfig.from_pretrained(args.bert_model)
        
        if args.model_type == "hierarchical":
            # 初始化一级和二级分类器
            level1_model = BertCRF(model_config, num_labels=len(level1_label_map))
            level2_model = BertCRF(model_config, num_labels=len(level2_label_map))
            
            # 初始化层次模型
            model = HierarchicalBertCRF(level1_model, level2_model)
        else:  # enhanced
            model = EnhancedHierarchicalBertCRF(model_config, len(level1_label_map), len(level2_label_map))
        
        model_file = os.path.join(args.model_path, "best_hierarchical_model.pt")
        logger.info(f"加载模型: {model_file}")
        model.load_state_dict(torch.load(model_file, map_location=device))
        model.to(device)
        
        # 预测
        logger.info("开始预测")
        result = hierarchical_predict(
            model, tokenizer, text, device, level1_id_to_label, level2_id_to_label, max_length=args.max_length
        )
        
        # 格式化结果
        output = []
        for token, level1_label, level2_label in result:
            output.append({
                "token": token,
                "level1_label": level1_label,
                "level2_label": level2_label
            })
    
    # 保存结果
    with open(args.output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    logger.info(f"预测结果保存至 {args.output_file}")
    
    return output

def main():
    """主函数"""
    # 解析参数
    args = parse_args()
    
    # 根据模式执行相应操作
    if args.mode == "preprocess":
        preprocess_mode(args)
    elif args.mode == "annotate":
        annotate_mode(args)
    elif args.mode == "train":
        train_mode(args)
    elif args.mode == "predict":
        predict_mode(args)
    else:
        logger.error(f"未知模式: {args.mode}")

if __name__ == "__main__":
    main()