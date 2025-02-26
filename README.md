# 关键信息提取系统

本系统使用规则和大型语言模型（LLM）从文本中提取关键信息。

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

### 使用测试脚本

#### 测试单个文件

```bash
python test_real_document.py --file your_file.txt --api_key "your_api_key" --model "gpt-3.5-turbo"
```

#### 测试目录中的所有文件

```bash
python test_real_document.py --dir your_directory --api_key "your_api_key"
```

## 支持的章节类型

- 标识部分
- 封装结构
- 芯片
- 键合系统
- 三、详细分析
- 四、附图

## 注意事项

1. 使用OpenAI API需要提供有效的API密钥
2. 如果LangChain库不可用，系统将使用正则表达式提取信息
3. 提取结果会自动评分，包括完整性和一致性评估 