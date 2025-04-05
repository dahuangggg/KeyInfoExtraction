# 专业文档关键要素自动识别和提取系统

基于大型语言模型（LLM）的专业文档关键要素自动识别和提取系统，使用 FastAPI 和 SQLAlchemy 实现的后端，提供了一套完整的文档处理、信息提取和知识库管理方案。

## 功能特性

- **文档管理**：支持单个或批量 Word 文档（.doc/.docx）上传、预览和管理
- **信息提取**：自动提取文档中的关键信息，包括物理状态组、物理状态名称、典型物理状态值、禁限用信息和测试评语
- **数据编辑与修正**：允许用户修改自动提取的结果，并记录修改历史
- **知识库构建**：将提取和复核后的数据存入知识库，辅助提取任务
- **数据导出**：支持将提取结果导出为 Excel 格式，所有物理状态组在一个工作表中，单元格内容居中显示

## 系统架构

系统分为前端和后端两部分：

- **前端**：基于Vue.js构建的用户界面，提供文档上传、结果查看和编辑功能
- **后端**：基于FastAPI的REST API服务，处理文档提取、数据持久化和知识库管理

系统采用三层架构：
1. **API 层**：处理 HTTP 请求和响应
2. **服务层**：实现业务逻辑
3. **数据层**：管理数据存储和检索

## 技术栈

- **Web 框架**：FastAPI
- **ORM**：SQLAlchemy
- **数据库**：SQLite
- **NLP/LLM**：大语言模型（如GPT）进行信息提取

## 安装与运行

### 环境要求

- Python 3.8+
- Node.js 14+

### 后端安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/KeyInfoExtraction.git
cd KeyInfoExtraction

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 启动后端服务
uvicorn app.main:app --reload
```

### 前端安装

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run serve
```

## 使用方法

### Web界面访问

启动前后端服务后，访问：
- 前端界面：http://localhost:8080
- API文档：http://localhost:8000/docs

### 命令行工具

系统也提供命令行工具，可直接处理文档：

```bash
# 处理单个文件
python backend/main.py --cli --file sample.docx

# 批量处理目录内的文档
python backend/main.py --cli --dir ./documents --format excel
```

## API设计

系统采用符合RESTful风格的API设计：

### 核心API端点

- **文档管理**
  - `POST /api/v1/documents` - 上传一个或多个文档
  - `GET /api/v1/documents` - 获取文档列表
  - `GET /api/v1/documents/{document_id}` - 获取文档详情
  - `DELETE /api/v1/documents/{document_id}` - 删除文档及关联数据

- **信息提取**
  - `POST /api/v1/extraction` - 创建提取任务
  - `GET /api/v1/extraction/{document_id}` - 获取提取结果（支持 `?format=xlsx` 参数下载 Excel）
  - `PUT /api/v1/extraction/{document_id}` - 更新提取结果
  - `POST /api/v1/extraction/test` - 测试提取功能
  - `POST /api/v1/extraction/batch` - 批量处理文档

- **知识库（辅助提取）**
  - `POST /api/v1/knowledge/documents/{document_id}` - 从文档提取结果创建知识库条目

- **编辑历史**
  - `GET /api/v1/edit-history/{document_id}` - 获取文档的编辑历史

## 配置说明

系统采用双重配置机制，通过`.env`文件和`app/core/config.py`共同管理配置项：

### 主要配置项

- **API 端点前缀**：`API_V1_STR`
- **数据库连接**：`SQLALCHEMY_DATABASE_URI`
- **文件上传目录**：`UPLOAD_DIR`
- **允许的文件类型**：`ALLOWED_EXTENSIONS`
- **LLM 配置**：
  - `LLM_MODE`: "api" 或 "server"，可选择使用API密钥或本地服务器
  - `LLM_API_KEY`: API模式下的密钥
  - `LLM_MODEL`: 使用的模型名称

## 部署说明

推荐使用Docker部署：

```bash
# 构建并启动服务
docker-compose up --build
```

## 开发指南

### 后端项目结构

```
backend/                           # 后端项目根目录
├── app/                           # 应用代码
│   ├── api/                       # API 路由
│   ├── core/                      # 核心配置
│   ├── db/                        # 数据库相关
│   ├── extractors/                # 信息提取器
│   ├── models/                    # 数据库模型
│   ├── schemas/                   # Pydantic 模式
│   ├── services/                  # 业务服务
│   ├── utils/                     # 工具函数
│   └── main.py                    # 应用入口
├── config/                        # 配置文件目录
├── output/                        # 输出文件目录
├── scripts/                       # 脚本文件目录
├── uploads/                       # 上传文件存储目录
└── README.md                      # 项目说明文档
```

### 数据库更新

需要更新数据库结构时，运行：

```bash
python backend/scripts/update_db_schema.py
```

## 贡献指南

1. Fork 本仓库
2. 创建功能分支：`git checkout -b my-new-feature`
3. 提交更改：`git commit -am 'Add some feature'`
4. 推送到分支：`git push origin my-new-feature`
5. 提交 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详细内容请参见 [LICENSE](LICENSE) 文件 