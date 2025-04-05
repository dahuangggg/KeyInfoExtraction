#!/bin/bash

# 预测脚本
python ../src/main.py --mode predict \
    --model_path ../output/models \
    --model_type hierarchical \
    --input_file ../examples/sample.txt \
    --output_file ../results/predictions.json