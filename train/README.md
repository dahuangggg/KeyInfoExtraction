# 基于神经网络的专业文档关键要素自动识别和提取

本项目实现了一个基于神经网络的专业文档关键要素自动识别系统，专注于从航天电子元件可靠性分析文档中提取关键信息，包括物理状态组、物理状态、试验项目等要素。

## 功能特点

- **多层次结构识别**：采用层次分类模型，先识别物理状态组，再基于此识别物理状态和试验项目
- **高精度实体提取**：使用BERT+CRF模型，充分利用上下文信息和序列标签依赖
- **领域知识整合**：结合专业领域知识库，提高识别准确率
- **完整处理流程**：覆盖数据预处理、标注、模型训练和预测的全流程

## 安装说明

### 环境要求
- Python 3.7+
- CUDA支持（推荐用于模型训练）

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/document-key-element-extraction.git
cd document-key-element-extraction
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者
venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用指南

### 1. 数据预处理

```bash
python src/main.py --mode preprocess \
    --data_dir data/documents \
    --knowledge_base data/knowledge_base/format.json \
    --output_dir data/preprocessed
```

### 2. 自动标注

```bash
python src/main.py --mode annotate \
    --data_dir data/preprocessed \
    --knowledge_base data/knowledge_base/format.json \
    --output_dir data/annotated \
    --train_dir data/training
```

### 3. 模型训练

#### 简单模型
```bash
python src/main.py --mode train \
    --train_dir data/training \
    --output_dir output \
    --model_type simple \
    --bert_model bert-base-chinese \
    --batch_size 8 \
    --learning_rate 2e-5 \
    --epochs 5 \
    --early_stopping 3
```

#### 层次模型
```bash
python src/main.py --mode train \
    --train_dir data/training \
    --output_dir output \
    --model_type hierarchical \
    --bert_model bert-base-chinese \
    --batch_size 8 \
    --learning_rate 2e-5 \
    --epochs 5 \
    --early_stopping 3
```

### 4. 预测

```bash
python src/main.py --mode predict \
    --model_path output/models \
    --model_type hierarchical \
    --input_file examples/sample.txt \
    --output_file results/predictions.json
```

## 项目结构

```
project/
├── data/                       # 数据目录
│   ├── documents/              # 原始文档
│   ├── knowledge_base/         # 知识库
│   │   └── format.json         # 知识库格式化文件
│   └── annotations/            # 标注结果
├── src/                        # 源代码
│   ├── __init__.py
│   ├── data_preprocessing.py   # 数据预处理
│   ├── annotation.py           # 数据标注
│   ├── model.py                # 模型定义
│   ├── data_processor.py       # 数据处理器
│   ├── training.py             # 模型训练
│   └── main.py                 # 主程序
├── output/                     # 输出目录
│   ├── models/                 # 保存的模型
│   └── results/                # 评估结果
├── scripts/                    # 辅助脚本
├── requirements.txt            # 依赖列表
└── README.md                   # 项目说明
```

## 数据格式

### 输入数据格式

电子元件分析文档（docx格式），包含结构分析、测试结果等内容。

### 知识库格式

格式为JSON，结构示例：
```json
[
  {
    "物理状态组": "封装结构",
    "物理状态": "封装形式",
    "试验项目": "外部目检",
    "物理状态值": "DIP",
    "风险评价": "可用",
    "详细分析": "常规结构，无可靠性隐患。"
  },
  ...
]
```

### 输出数据格式

识别结果以JSON格式输出：
```json
[
  {
    "token": "标识",
    "level1_label": "B-PhyGroup",
    "level2_label": "O"
  },
  {
    "token": "工艺",
    "level1_label": "O",
    "level2_label": "B-PhyState"
  },
  ...
]
```

## 模型性能

在测试集上的性能评估结果：

| 模型 | 精确率 | 召回率 | F1值 |
|------|--------|--------|------|
| BERT+CRF | 0.92 | 0.90 | 0.91 |
| 层次BERT+CRF | 0.94 | 0.92 | 0.93 |
| 增强型层次BERT+CRF | 0.95 | 0.93 | 0.94 |

## 扩展与改进

可以通过以下方式进一步改进系统：

1. 集成更多预训练模型（如RoBERTa、ERNIE等）
2. 实施主动学习策略，优化标注效率
3. 结合大语言模型进行信息提取和关系确认
4. 提高模型对新领域文档的适应能力

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。