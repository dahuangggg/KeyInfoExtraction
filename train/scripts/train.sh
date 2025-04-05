#!/bin/bash

# 模型训练脚本
python ../src/main.py --mode train \
    --train_dir ../data/training \
    --output_dir ../output \
    --model_type hierarchical \
    --bert_model bert-base-chinese \
    --batch_size 8 \
    --learning_rate 2e-5 \
    --epochs 5 \
    --early_stopping 3