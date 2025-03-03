# 关键信息提取系统

本系统使用规则和大型语言模型（LLM）从文本中提取关键信息，专注于元器件物理状态信息的结构化提取。

## 安装

1. 克隆仓库
```bash
git clone https://github.com/yourusername/KeyInfoExtraction.git
cd KeyInfoExtraction
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

## 数据文件

项目包含以下数据文件：

- `data/samples/`: 包含示例文本文件，用于测试提取功能
- `data/nlp_static/`: 包含NLP相关的静态资源文件
  - `stopwords.txt`: 中文停用词表，用于文本预处理
  - `proper_nouns.txt`: 专有名词词典，用于实体识别
- `data/labeled_data/`: 包含用于训练自定义模型的标注数据（由训练脚本生成）

## 使用方法

### 使用LLMExtractor提取信息

LLMExtractor支持使用OpenAI API或本地模型提取信息。

#### 基本用法

```python
from extractors.llm_extractor import LLMExtractor

# 使用OpenAI API
extractor = LLMExtractor(
    model_name="gpt-3.5-turbo",
    use_api=True,
    api_key="your_api_key"
)

# 提取信息
text = "标识部分：器件型号规格为XC9536，生产批次为2023-A..."
result = extractor.extract_info(text, "标识部分")
print(result)
```

#### 多模型集成

```python
# 使用多个模型集成提取
models = ["gpt-3.5-turbo", "gpt-4"]
result = extractor.extract_info_ensemble(text, "标识部分", models=models)
```

#### 异步提取

```python
import asyncio

# 异步提取
result = asyncio.run(extractor.extract_info_async(text, "标识部分"))
```

### 使用命令行工具

#### 处理单个文件

```bash
python main.py --file your_file.docx --output output_dir
```

#### 处理目录中的所有文件

```bash
python main.py --dir your_directory --output output_dir
```

#### 使用自定义训练的模型

```bash
python main.py --file your_file.docx --output output_dir --use_custom_models
```

## 支持的章节类型

- 标识部分
- 封装结构
- 芯片
- 键合系统
- 三、详细分析
- 四、附图（会被忽略）

## 自定义模型训练

本项目支持训练自定义模型来提取元器件物理状态信息，无需依赖外部API。

### 训练脚本目录结构

```
training_scripts/
├── prepare_data.py       # 数据准备脚本
├── train_ner_model.py    # NER模型训练脚本
├── train_relation_model.py # 关系抽取模型训练脚本
├── evaluate_models.py    # 模型评估脚本
└── run_training.sh       # 一键运行脚本
```

### 训练流程

#### 1. 数据准备

数据准备脚本会从`data`目录中的文档提取文本，并生成用于训练的标注数据：

```bash
python training_scripts/prepare_data.py
```

生成的数据将保存在`data/labeled_data`目录下，包括：
- `ner_training_data.json`: 完整的NER训练数据
- `ner_train.json`, `ner_dev.json`, `ner_test.json`: 划分后的NER数据集
- `relation_training_data.json`: 完整的关系抽取训练数据
- `relation_train.json`, `relation_dev.json`, `relation_test.json`: 划分后的关系抽取数据集

#### 2. 训练NER模型

训练命名实体识别模型，用于识别文本中的物理状态名称、典型物理状态值和禁限用信息：

```bash
python training_scripts/train_ner_model.py \
    --train_file data/labeled_data/ner_train.json \
    --dev_file data/labeled_data/ner_dev.json \
    --model_name_or_path bert-base-chinese \
    --output_dir models/ner \
    --batch_size 8 \
    --learning_rate 2e-5 \
    --epochs 3
```

#### 3. 训练关系抽取模型

训练关系抽取模型，用于识别实体之间的关系：

```bash
python training_scripts/train_relation_model.py \
    --train_file data/labeled_data/relation_train.json \
    --dev_file data/labeled_data/relation_dev.json \
    --model_name_or_path bert-base-chinese \
    --output_dir models/relation \
    --batch_size 8 \
    --learning_rate 2e-5 \
    --epochs 3
```

#### 4. 评估模型

评估训练好的模型在测试集上的性能：

```bash
python training_scripts/evaluate_models.py \
    --ner_model_path models/ner \
    --relation_model_path models/relation \
    --ner_test_file data/labeled_data/ner_test.json \
    --relation_test_file data/labeled_data/relation_test.json
```

#### 5. 在文档上测试

在实际文档上测试模型的提取效果：

```bash
python training_scripts/evaluate_models.py \
    --ner_model_path models/ner \
    --relation_model_path models/relation \
    --doc_path test.docx
```

### 一键运行训练流程

可以使用提供的脚本一键完成整个训练和评估流程：

```bash
bash training_scripts/run_training.sh
```

### 自定义训练参数

可以通过修改训练脚本中的参数来调整模型性能：

- `--model_name_or_path`: 预训练模型名称或路径，可以使用其他中文预训练模型
- `--batch_size`: 批次大小，根据GPU内存调整
- `--learning_rate`: 学习率
- `--epochs`: 训练轮数
- `--max_length`: 最大序列长度

### 使用自己的数据

如果要使用自己的数据进行训练，需要：

1. 将文档放入`data`目录
2. 修改`prepare_data.py`中的实体和关系模式，以适应您的数据特点
3. 运行训练流程

## 注意事项

1. 使用OpenAI API需要提供有效的API密钥
2. 如果LangChain库不可用，系统将使用正则表达式提取信息
3. 提取结果会自动评分，包括完整性和一致性评估
4. 训练自定义模型需要GPU加速，建议使用具有至少8GB显存的GPU
5. 首次运行训练脚本时会下载预训练模型，需要稳定的网络连接
6. 完整训练可能需要几个小时，具体时间取决于数据量和硬件配置 