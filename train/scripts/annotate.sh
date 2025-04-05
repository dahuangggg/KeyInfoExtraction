#!/bin/bash

# 自动标注脚本
python ../src/main.py --mode annotate \
    --data_dir ../data/preprocessed \
    --knowledge_base ../data/knowledge_base/format.json \
    --output_dir ../data/annotated \
    --train_dir ../data/training