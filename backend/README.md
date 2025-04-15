# 专业文档关键要素自动识别和提取系统 - 后端

## 项目概述

本项目是一个基于大型语言模型（LLM）的专业文档关键要素自动识别和提取系统的后端部分。系统能够自动分析文档内容，识别并提取物理状态相关的关键信息，并提供编辑、存储和导出功能。采用FastAPI和SQLAlchemy构建，具有高性能、可扩展的特点。

### 主要目标

- 减少手动提取文档关键信息的工作量
- 提高信息提取的一致性和准确性
- 建立专业领域的知识库，辅助后续提取任务
- 提供友好的用户界面进行数据管理和编辑

## 功能特性

- **文档管理**：支持单个或批量 Word 文档（.doc/.docx）上传、预览和管理
- **信息提取**：自动提取文档中的关键信息，包括物理状态组、物理状态名称、典型物理状态值、禁限用信息和测试评语
- **数据编辑与修正**：允许用户修改自动提取的结果，并记录修改历史
- **知识库构建**：将提取和复核后的数据存入知识库，辅助提取任务
- **数据导出**：支持将提取结果导出为 Excel 格式，所有物理状态组在一个工作表中，单元格内容居中显示

## 技术栈

- **Web 框架**：FastAPI
- **ORM**：SQLAlchemy
- **数据库**：SQLite/MySQL
- **NLP/LLM**：命名实体识别（NER）和大语言模型（GPT）进行信息提取
- **并行处理**：使用concurrent.futures实现多线程处理

## 提取系统架构

系统采用多Agent协作架构进行文档信息提取，通过分工合作提高提取准确性和灵活性：

### 多Agent提取架构

系统包含四个专业化的Agent，每个Agent负责特定任务，协同工作完成整个提取过程：

1. **协调Agent（CoordinatorAgent）**
   - 整体流程管理与调度
   - 组织和分发文档处理任务
   - 协调各专业Agent的工作
   - 汇总并格式化最终输出结果

2. **识别Agent（IdentificationAgent）**
   - 负责从文档中初步识别物理状态组和物理状态
   - 支持多种识别策略（规则识别、NER识别、LLM识别）
   - 构建初始的物理状态组结构图
   - 为提取Agent准备结构化的识别目标

3. **提取Agent（ExtractionAgent）**
   - 基于识别结果深入提取具体的物理状态值
   - 提取相关的风险评价和测试评语
   - 支持并行批量处理多个提取任务
   - 按物理状态组分组处理，提高效率

4. **验证Agent（ValidationAgent）**
   - 验证提取结果的完整性和一致性
   - 应用领域特定规则进行内容校正
   - 自动拆分和优化复杂的提取结果
   - 生成最终标准化的输出数据

### 处理流程

1. 文档上传完成后，由CoordinatorAgent接管整个处理流程
2. IdentificationAgent首先扫描文档，识别所有物理状态组和物理状态项
3. ExtractionAgent根据识别结果，从文档中提取详细信息
4. ValidationAgent验证和优化提取结果，确保数据质量
5. CoordinatorAgent整合所有结果并返回标准格式的数据

### 核心优势

- **分布式处理**：各Agent专注于特定任务，提高整体处理质量
- **并行提取**：利用多线程技术并行处理不同的物理状态组
- **自适应识别**：结合规则和LLM能力，适应不同文档结构
- **容错机制**：内置多层验证和修复逻辑，提高结果可靠性
- **可扩展性**：模块化设计使系统易于扩展和优化

## 安装与运行

### 环境要求

- Python 3.8+
- 支持Windows/Linux/macOS系统
- LibreOffice (用于文档处理)

### 安装步骤

1. 克隆项目代码
   ```bash
   git clone https://github.com/dahuangggg/KeyInfoExtraction.git
   cd KeyInfoExtraction
   ```

2. 创建并激活虚拟环境（可选但推荐）
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. 安装依赖
   ```bash
   pip install -r backend/requirements.txt
   ```

4. 配置环境变量（可选）
   - 可以创建`.env`文件在backend目录下配置数据库连接等信息
   - 或直接使用默认配置(backend/app/core/config.py)进行开发测试

### 运行服务器

```bash
cd backend
python main.py
```

默认情况下，服务器将在`http://localhost:8000`启动，可以通过`--host`和`--port`参数自定义地址和端口。

### 命令行参数接口

系统支持通过命令行参数进行配置，可通过以下方式查看可用参数：

```bash
python main.py --help
```

#### 服务器参数

```
--host HOST               # 服务器主机地址，默认为0.0.0.0
--port PORT               # 服务器端口，默认为8000
--reload                  # 启用热重载（开发模式）
```

#### 命令行模式参数

```
--cli                     # 使用命令行模式而不是API服务器
--file FILE               # 要处理的单个文件路径
--dir DIR                 # 要批量处理的目录路径
--output OUTPUT           # 输出目录，默认为./output
--format {json,excel,both} # 输出格式，默认为json
```

#### LLM模型参数

```
--server_ip SERVER_IP     # LLM服务器IP地址，默认使用settings.LLM_SERVER_IP
--server_port SERVER_PORT # LLM服务器端口，默认使用settings.LLM_SERVER_PORT
--model_name MODEL_NAME   # LLM模型名称，默认使用settings.LLM_MODEL
--api_key API_KEY         # LLM API密钥，默认使用settings.LLM_API_KEY
--debug                   # 启用调试模式
--use_local_api           # 使用本地API而不是云API
```

#### 命令行模式示例

```bash
# 处理单个文件
python backend/main.py --cli --file sample.docx

# 批量处理目录内的文档并导出为Excel格式
python backend/main.py --cli --dir ./documents --format excel

# 使用自定义LLM服务器
python backend/main.py --cli --file sample.docx --server_ip 127.0.0.1 --server_port 8080 --model_name gpt-4 --use_local_api
```

## API 文档

启动服务器后，可以通过以下 URL 访问 API 文档：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

## 核心 API 端点

### 文档管理

- `POST /api/v1/documents` - 上传一个或多个文档
- `GET /api/v1/documents` - 获取文档列表
- `GET /api/v1/documents/{document_id}` - 获取文档详情
- `GET /api/v1/documents/content/{document_id}` - 获取文档内容
- `DELETE /api/v1/documents/{document_id}` - 删除文档及关联数据

### 信息提取

- `POST /api/v1/extraction` - 创建提取任务
- `GET /api/v1/extraction/{document_id}` - 获取提取结果（支持 `?format=xlsx` 参数下载 Excel）
- `PUT /api/v1/extraction/{document_id}` - 更新提取结果
- `POST /api/v1/extraction/test` - 测试提取功能
- `POST /api/v1/extraction/batch` - 批量处理文档

### 知识库（辅助提取）

- `POST /api/v1/knowledge/documents/{document_id}` - 从文档提取结果创建知识库条目

### 编辑历史

- `GET /api/v1/edit-history/{document_id}` - 获取文档的编辑历史

## 项目结构

```
backend/                           # 后端项目根目录
├── app/                           # 应用代码
│   ├── api/                       # API 路由
│   │   ├── deps.py                # 依赖注入
│   │   └── v1/                    # API v1 版本
│   │       ├── __init__.py        # 初始化文件
│   │       ├── documents.py       # 文档管理 API
│   │       ├── edit_history.py    # 编辑历史 API
│   │       ├── extraction.py      # 信息提取 API
│   │       └── knowledge_base.py  # 知识库 API
│   ├── core/                      # 核心配置
│   │   ├── __init__.py            # 初始化文件
│   │   └── config.py              # 配置管理
│   ├── db/                        # 数据库相关
│   │   ├── __init__.py            # 初始化文件
│   │   ├── base.py                # 数据库基础模型
│   │   ├── base_class.py          # 基础类
│   │   └── session.py             # 数据库会话
│   ├── extractors/                # 信息提取器
│   │   ├── __init__.py            # 初始化文件
│   │   ├── base_extractor.py      # 基础提取器
│   │   ├── llm_extractor.py       # 大语言模型提取器
│   │   ├── llm_service.py         # LLM服务接口
│   │   ├── rule_extractor.py      # 规则提取器
│   │   └── multi_agent/           # 多Agent架构
│   │       ├── __init__.py        # 初始化文件
│   │       ├── coordinator_agent.py # 协调Agent
│   │       ├── identification_agent.py # 识别Agent
│   │       ├── extraction_agent.py # 提取Agent
│   │       ├── validation_agent.py # 验证Agent
│   │       └── prompts/           # 提示模板
│   ├── models/                    # 数据库模型
│   │   ├── __init__.py            # 初始化文件
│   │   ├── document.py            # 文档模型
│   │   ├── edit_history.py        # 编辑历史模型
│   │   ├── extraction.py          # 提取结果模型
│   │   └── knowledge_base.py      # 知识库模型
│   ├── schemas/                   # Pydantic 模式
│   │   ├── document.py            # 文档模式
│   │   ├── extraction.py          # 提取结果模式
│   │   └── knowledge.py           # 知识库模式
│   ├── services/                  # 业务服务
│   │   ├── __init__.py            # 初始化文件
│   │   ├── document_service.py    # 文档服务
│   │   ├── edit_history_service.py # 编辑历史服务
│   │   ├── extraction_service.py  # 信息提取服务
│   │   └── knowledge_service.py   # 知识库服务
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py            # 初始化文件
│   │   ├── data_utils.py          # 数据处理工具
│   │   ├── doc_processor.py       # 文档处理工具
│   │   ├── excel_utils.py         # Excel 处理工具
│   │   └── file_utils.py          # 文件处理工具
│   └── main.py                    # 应用入口
├── config/                        # 配置文件目录
│   ├── format.json                # 格式定义文件
│   └── terminology.txt            # 术语文件
├── output/                        # 输出文件目录
├── scripts/                       # 脚本文件目录
│   └── update_db_schema.py        # 数据库结构更新脚本
├── tests/                         # 测试目录
├── uploads/                       # 上传文件存储目录
├── .env                           # 环境变量配置
├── .gitignore                     # Git 忽略文件
├── README.md                      # 项目说明文档
├── key_info_extraction.db         # SQLite 数据库文件
├── main.py                        # 主入口文件
└── requirements.txt               # 依赖需求
```

## 配置项说明

系统采用双重配置机制，通过`.env`文件和`app/core/config.py`共同管理配置项：

- **`.env`文件**：存储环境相关的变量值。通过修改此文件来覆盖默认设置，而无需修改代码。

- **`app/core/config.py`**：定义所有配置项的默认值，通过`Settings`类实现。该类使用`pydantic_settings`库将`.env`文件中的值自动加载并覆盖默认值。

主要配置项包括：

- **API 端点前缀**：`API_V1_STR`
- **数据库连接**：`SQLALCHEMY_DATABASE_URI`
- **文件上传目录**：`UPLOAD_DIR`
- **允许的文件类型**：`ALLOWED_EXTENSIONS`
- **LLM 配置**：
  - `LLM_MODE`: "api" 或 "server"，分别表示使用 API 密钥或本地服务器
  - `LLM_API_KEY`: API 模式下的密钥
  - `LLM_MODEL`: API 模式下使用的模型名称
  - `LLM_SERVER_IP` 和 `LLM_SERVER_PORT`: 服务器模式下的连接信息
  - `LLM_SERVER_MODEL`: 服务器模式下使用的模型名称

## 系统架构

系统采用三层架构：

1. **API 层**：处理 HTTP 请求和响应
2. **服务层**：实现业务逻辑
3. **数据层**：管理数据存储和检索

其中，关键业务流程是文档提取处理，由以下步骤组成：

1. 文档上传并保存到数据库
2. 创建提取任务，异步处理文档
3. LLM 提取器分析文档内容并提取关键信息
   - 多Agent架构协同工作完成信息提取
   - 先识别状态组和状态，再提取具体值
   - 最后验证结果完整性和合理性
4. 提取结果保存到数据库并可被查询、导出或编辑

## 快速开始

### 使用Docker (推荐)

```bash
# 构建和启动服务
docker-compose up -d

# 检查服务状态
docker-compose ps

### 手动安装

1. 安装系统依赖

```bash
# Debian/Ubuntu
apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    antiword \
    poppler-utils \
    tesseract-ocr \
    fonts-wqy-microhei \
    fonts-wqy-zenhei
```

2. 安装Python依赖

```bash
pip install -r requirements.txt
```

3. 运行应用

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
