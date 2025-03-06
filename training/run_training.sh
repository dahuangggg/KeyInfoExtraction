#!/bin/bash

# 设置环境变量
export PYTHONPATH=$(pwd):$PYTHONPATH

# 创建必要的目录
mkdir -p models/ner models/relation data/labeled_data

# 步骤1: 准备数据
echo "===== 步骤1: 准备训练数据 ====="
python training_scripts/prepare_data.py

# 步骤2: 训练NER模型
echo "===== 步骤2: 训练NER模型 ====="
python training_scripts/train_ner_model.py \
    --train_file data/labeled_data/ner_train.json \
    --dev_file data/labeled_data/ner_dev.json \
    --model_name_or_path bert-base-chinese \
    --output_dir models/ner \
    --batch_size 8 \
    --learning_rate 2e-5 \
    --epochs 3

# 步骤3: 训练关系抽取模型
echo "===== 步骤3: 训练关系抽取模型 ====="
python training_scripts/train_relation_model.py \
    --train_file data/labeled_data/relation_train.json \
    --dev_file data/labeled_data/relation_dev.json \
    --model_name_or_path bert-base-chinese \
    --output_dir models/relation \
    --batch_size 8 \
    --learning_rate 2e-5 \
    --epochs 3

# 步骤4: 评估模型
echo "===== 步骤4: 评估模型 ====="
python training_scripts/evaluate_models.py \
    --ner_model_path models/ner \
    --relation_model_path models/relation \
    --ner_test_file data/labeled_data/ner_test.json \
    --relation_test_file data/labeled_data/relation_test.json

# 步骤5: 在测试文档上评估
echo "===== 步骤5: 在测试文档上评估 ====="
python training_scripts/evaluate_models.py \
    --ner_model_path models/ner \
    --relation_model_path models/relation \
    --doc_path test.docx

# 步骤6: 使用训练好的模型处理文档
echo "===== 步骤6: 使用训练好的模型处理文档 ====="
python main.py --file test.docx --output test_output_custom_model --use_custom_models

echo "训练和评估流程完成！" 