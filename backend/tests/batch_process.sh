#!/bin/bash

# 批量处理文件夹中的文件

# 设置默认参数
INPUT_DIR="../../train/data/documents"
FORMAT_JSON="../data_static/format.json"
API_KEY="YOUR_API_KEY_HERE"
MODEL="gpt-3.5-turbo"
OUTPUT_DIR="batch_results"
FILE_PATTERN="*.docx"
LIMIT=0
SLEEP_TIME=1

# 显示帮助信息
show_help() {
    echo "批量处理文件夹中的文件"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -i, --input-dir DIR      输入文件目录 (默认: $INPUT_DIR)"
    echo "  -f, --format-json FILE   格式定义JSON文件路径 (默认: $FORMAT_JSON)"
    echo "  -k, --api-key KEY        API密钥 (必需)"
    echo "  -b, --api-base URL       API基础URL (可选)"
    echo "  -m, --model NAME         模型名称 (默认: $MODEL)"
    echo "  -o, --output-dir DIR     输出目录 (默认: $OUTPUT_DIR)"
    echo "  -p, --pattern PATTERN    文件匹配模式 (默认: $FILE_PATTERN)"
    echo "  -l, --limit NUMBER       处理文件数量限制，0表示处理所有文件 (默认: $LIMIT)"
    echo "  -s, --sleep SECONDS      两次API调用之间的休眠时间（秒）(默认: $SLEEP_TIME)"
    echo "  -h, --help               显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0 --api-key sk-xxxx --input-dir ./documents --format-json ./format.json"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        -f|--format-json)
            FORMAT_JSON="$2"
            shift 2
            ;;
        -k|--api-key)
            API_KEY="$2"
            shift 2
            ;;
        -b|--api-base)
            API_BASE="$2"
            shift 2
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -p|--pattern)
            FILE_PATTERN="$2"
            shift 2
            ;;
        -l|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -s|--sleep)
            SLEEP_TIME="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查必需参数
if [ -z "$API_KEY" ]; then
    echo "错误: 必须提供API密钥"
    show_help
    exit 1
fi

if [ ! -d "$INPUT_DIR" ]; then
    echo "错误: 输入目录 $INPUT_DIR 不存在"
    exit 1
fi

if [ ! -f "$FORMAT_JSON" ]; then
    echo "错误: 格式JSON文件 $FORMAT_JSON 不存在"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 获取匹配的文件列表
FILES=($INPUT_DIR/$FILE_PATTERN)

# 检查是否找到文件
if [ ${#FILES[@]} -eq 0 ]; then
    echo "未找到匹配的文件: $INPUT_DIR/$FILE_PATTERN"
    exit 1
fi

# 如果设置了限制，则只处理指定数量的文件
if [ "$LIMIT" -gt 0 ] && [ "$LIMIT" -lt ${#FILES[@]} ]; then
    FILES=("${FILES[@]:0:$LIMIT}")
fi

echo "找到 ${#FILES[@]} 个匹配的文件"

# 创建结果摘要文件
SUMMARY_FILE="$OUTPUT_DIR/batch_summary.txt"
echo "批处理摘要" > "$SUMMARY_FILE"
echo "总文件数: ${#FILES[@]}" >> "$SUMMARY_FILE"
echo "开始时间: $(date)" >> "$SUMMARY_FILE"
echo "----------------------------" >> "$SUMMARY_FILE"

# 计数器
TOTAL=${#FILES[@]}
SUCCESS=0
FAILED=0

# 处理每个文件
for ((i=0; i<${#FILES[@]}; i++)); do
    FILE="${FILES[$i]}"
    FILENAME=$(basename "$FILE")
    
    echo -e "\n[$((i+1))/$TOTAL] 处理文件: $FILENAME"
    
    # 构建命令
    CMD="python test_extract_api_key.py \"$FILE\" \"$FORMAT_JSON\" --api-key \"$API_KEY\" --model \"$MODEL\" --output-dir \"$OUTPUT_DIR\""
    
    # 如果指定了API基础URL，则添加到命令中
    if [ ! -z "$API_BASE" ]; then
        CMD="$CMD --api-base \"$API_BASE\""
    fi
    
    # 执行命令
    START_TIME=$(date +%s)
    eval $CMD > "$OUTPUT_DIR/${FILENAME}.log" 2>&1
    EXIT_CODE=$?
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # 检查执行结果
    if [ $EXIT_CODE -eq 0 ]; then
        echo "处理成功: $FILENAME (耗时: ${ELAPSED}秒)"
        STATUS="成功"
        ((SUCCESS++))
    else
        echo "处理失败: $FILENAME (耗时: ${ELAPSED}秒)"
        echo "查看日志: $OUTPUT_DIR/${FILENAME}.log"
        STATUS="失败"
        ((FAILED++))
    fi
    
    # 添加到摘要
    echo "[$((i+1))/$TOTAL] $FILENAME: $STATUS (耗时: ${ELAPSED}秒)" >> "$SUMMARY_FILE"
    
    # 更新摘要统计
    echo -e "\n当前统计:" >> "$SUMMARY_FILE"
    echo "- 总文件数: $TOTAL" >> "$SUMMARY_FILE"
    echo "- 已处理: $((i+1))" >> "$SUMMARY_FILE"
    echo "- 成功: $SUCCESS" >> "$SUMMARY_FILE"
    echo "- 失败: $FAILED" >> "$SUMMARY_FILE"
    echo "----------------------------" >> "$SUMMARY_FILE"
    
    # 在两次API调用之间休眠，以避免API速率限制
    if [ $i -lt $((${#FILES[@]}-1)) ] && [ "$SLEEP_TIME" -gt 0 ]; then
        echo "休眠 $SLEEP_TIME 秒..."
        sleep "$SLEEP_TIME"
    fi
done

# 添加最终摘要
echo -e "\n最终摘要:" >> "$SUMMARY_FILE"
echo "总文件数: $TOTAL" >> "$SUMMARY_FILE"
echo "处理成功: $SUCCESS" >> "$SUMMARY_FILE"
echo "处理失败: $FAILED" >> "$SUMMARY_FILE"
echo "完成时间: $(date)" >> "$SUMMARY_FILE"

# 输出最终结果
echo -e "\n批处理完成:"
echo "- 总文件数: $TOTAL"
echo "- 处理成功: $SUCCESS"
echo "- 处理失败: $FAILED"
echo "- 摘要已保存到: $SUMMARY_FILE" 