#!/bin/bash

# 预处理脚本
python ../src/main.py --mode preprocess \
    --data_dir ../data/documents \
    --knowledge_base ../data/knowledge_base/format.json \
    --output_dir ../data/preprocessed