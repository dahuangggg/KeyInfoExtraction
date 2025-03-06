# 专业文档关键要素自动识别和提取系统 - 后端

基于神经网络的专业文档关键要素自动识别和提取系统的后端部分，使用 FastAPI 和 SQLAlchemy 实现。

## 功能特性

- **文档管理**：支持单个或批量 Word 文档（.doc/.docx）上传、预览和管理
- **信息提取**：自动提取文档中的关键信息，包括物理状态组、物理状态名称、典型物理状态值、禁限用信息和测试评语
- **数据编辑与修正**：允许用户修改自动提取的结果，并记录修改历史
- **知识库构建**：将提取和复核后的数据存入知识库，支持知识库的管理和查询
- **数据导出**：支持将提取结果导出为 Excel 格式

## 技术栈

- **Web 框架**：FastAPI
- **ORM**：SQLAlchemy
- **数据库**：SQLite（可扩展至 PostgreSQL 等）
- **NLP/LLM**：结合命名实体识别（NER）和大语言模型（如 GPT 系列）进行信息提取

## 安装与运行

### 环境要求

- Python 3.8+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行服务器

```bash
# API 服务器模式
python main.py

# 自定义主机和端口
python main.py --host 127.0.0.1 --port 8080

# 开发模式（启用热重载）
python main.py --reload
```

### 命令行模式

除了 API 服务器模式外，还支持命令行模式直接处理文档：

```bash
# 处理单个文档
python main.py --cli --file path/to/document.docx

# 批量处理目录中的文档
python main.py --cli --dir path/to/documents

# 指定输出格式（json、excel 或 both）
python main.py --cli --file path/to/document.docx --format excel

# 使用自定义模型
python main.py --cli --file path/to/document.docx --use_custom_models --ner_model ./models/ner --relation_model ./models/relation
```

## API 文档

启动服务器后，可以通过以下 URL 访问 API 文档：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

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
│   │       └── knowledge.py       # 知识库 API
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
│   │   └── rule_extractor.py      # 规则提取器
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
├── migrations/                    # 数据库迁移
├── models/                        # 模型存储目录
├── output/                        # 输出文件目录
├── tests/                         # 测试代码
├── uploads/                       # 上传文件存储目录
├── .env                           # 环境变量配置
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git 忽略文件
├── Dockerfile                     # Docker 配置
├── README.md                      # 项目说明文档
├── docker-compose.yml             # Docker Compose 配置
├── key_info_extraction.db         # SQLite 数据库文件
├── main.py                        # 主入口文件
└── requirements.txt               # 依赖需求
```

## 文件说明

### 配置文件

- **requirements.txt**: 列出项目所需的所有 Python 依赖包
- **.env**: 环境变量配置文件，包含 API 密钥、数据库连接等敏感信息
- **.env.example**: 环境变量示例文件，用于指导用户如何配置自己的 .env 文件
- **Dockerfile**: 用于构建 Docker 镜像的配置文件
- **docker-compose.yml**: 定义和运行多容器 Docker 应用程序的配置文件

### 核心应用文件

- **main.py**: 项目主入口文件，处理命令行参数和启动服务器
- **app/main.py**: FastAPI 应用程序的入口点，设置中间件、路由和异常处理
- **app/core/config.py**: 应用程序配置管理，从环境变量加载设置

### 数据库相关

- **app/db/session.py**: 数据库会话管理
- **app/db/base_class.py**: SQLAlchemy 基础模型类
- **app/db/base.py**: 导入所有模型以便 Alembic 可以检测到它们
- **key_info_extraction.db**: SQLite 数据库文件

### 模型和模式

- **app/models/**: 包含 SQLAlchemy ORM 模型，定义数据库表结构
- **app/schemas/**: 包含 Pydantic 模型，用于数据验证和序列化

### API 路由

- **app/api/deps.py**: 依赖注入函数，如获取数据库会话
- **app/api/v1/**: 包含所有 API 端点的路由处理器

### 业务逻辑

- **app/services/**: 包含业务逻辑服务，处理数据库操作和业务规则
- **app/extractors/**: 包含信息提取器，负责从文档中提取关键信息

### 工具函数

- **app/utils/**: 包含各种工具函数，如文件处理、数据转换等

## 开发指南

### 数据库迁移

使用 Alembic 进行数据库迁移：

```bash
# 初始化迁移
alembic init migrations

# 创建迁移脚本
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head
```

### 测试

```bash
pytest
```

### Docker 部署

```bash
# 构建并启动服务
docker-compose up --build

# 仅启动服务（不重新构建）
docker-compose up

# 在后台运行
docker-compose up -d
``` 