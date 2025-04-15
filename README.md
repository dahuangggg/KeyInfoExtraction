# 专业文档关键要素自动识别和提取系统

基于大型语言模型（LLM）的专业文档关键要素自动识别和提取系统。本系统能够自动分析文档内容，识别并提取物理状态相关的关键信息，并提供编辑、存储和导出功能。

## 系统架构

系统分为前端和后端两部分：

- **[前端](./frontend/README.md)**：基于Vue 3和Element Plus构建的用户界面，提供文档上传、结果查看和编辑功能（作为Git子模块引用）
- **[后端](./backend/README.md)**：基于FastAPI的REST API服务，处理文档提取、数据持久化和知识库管理

## 功能特性

- **文档管理**：支持单个或批量 Word 文档（.doc/.docx）上传、预览和管理
- **信息提取**：自动提取文档中的关键信息，包括物理状态组、物理状态名称、典型物理状态值、禁限用信息和测试评语
- **数据编辑与修正**：允许用户修改自动提取的结果，并记录修改历史
- **知识库构建**：将提取和复核后的数据存入知识库，辅助提取任务
- **数据导出**：支持将提取结果导出为 Excel 格式，所有物理状态组在一个工作表中，单元格内容居中显示

## 技术栈

### 后端技术栈
- **Web 框架**：FastAPI
- **ORM**：SQLAlchemy
- **数据库**：SQLite/MySQL
- **NLP/LLM**：命名实体识别（NER）和大语言模型（GPT）进行信息提取
- **并行处理**：使用concurrent.futures实现多线程处理

### 前端技术栈
- **框架**：Vue 3
- **构建工具**：Vite
- **UI组件库**：Element Plus
- **路由**：Vue Router
- **HTTP客户端**：Axios
- **CSS预处理器**：SCSS

## 安装与运行

### 环境要求

- Python 3.8+
- Node.js 16+
- npm 7+ 或 yarn 1.22+
- LibreOffice (用于文档处理)

### 克隆项目

```bash
# 克隆主仓库
git clone https://github.com/dahuangggg/KeyInfoExtraction.git
cd KeyInfoExtraction

# 初始化并更新前端子模块
git submodule init
git submodule update
```

如果希望在克隆时直接获取所有子模块，可以使用：

```bash
git clone --recurse-submodules https://github.com/dahuangggg/KeyInfoExtraction.git
cd KeyInfoExtraction
```

### 后端安装

```bash
# 创建并激活虚拟环境（可选但推荐）
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 安装依赖
pip install -r backend/requirements.txt

# 运行服务器
cd backend
python main.py
```

详细的后端配置和参数选项请参阅 [后端README](./backend/README.md)。

### 前端安装

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

详细的前端开发和构建信息请参阅 [前端README](./frontend/README.md)。

## Docker部署

推荐使用Docker Compose进行部署：

```bash
# 构建并启动服务
docker-compose up --build
```

## 使用方法

### Web界面访问

启动前后端服务后，访问：
- 前端界面：http://localhost:5173
- API文档：http://localhost:8000/docs

### 命令行工具

系统也提供命令行工具，可直接处理文档：

```bash
# 处理单个文件
python backend/main.py --cli --file sample.docx

# 批量处理目录内的文档
python backend/main.py --cli --dir ./documents --format excel
```

## 多Agent提取架构

系统采用多Agent协作架构进行文档信息提取，通过分工合作提高提取准确性和灵活性：

### Agent结构

1. **协调Agent（CoordinatorAgent）**：整体流程管理与调度
2. **识别Agent（IdentificationAgent）**：负责从文档中初步识别物理状态组和物理状态
3. **提取Agent（ExtractionAgent）**：基于识别结果深入提取具体的物理状态值
4. **验证Agent（ValidationAgent）**：验证提取结果的完整性和一致性

详细的架构设计请参阅 [后端README](./backend/README.md)。

## API文档

启动后端服务器后，可以通过以下URL访问API文档：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

## 项目结构

### 后端项目结构

```
backend/                           # 后端项目根目录
├── app/                           # 应用代码
│   ├── api/                       # API 路由
│   ├── core/                      # 核心配置
│   ├── db/                        # 数据库相关
│   ├── extractors/                # 信息提取器
│   │   └── multi_agent/           # 多Agent架构
│   ├── models/                    # 数据库模型
│   ├── schemas/                   # Pydantic 模式
│   ├── services/                  # 业务服务
│   └── utils/                     # 工具函数
├── config/                        # 配置文件目录
├── output/                        # 输出文件目录
├── scripts/                       # 脚本文件目录
├── uploads/                       # 上传文件存储目录
└── README.md                      # 项目说明文档
```

### 前端项目结构

```
frontend/                         # 前端项目根目录
├── public/                       # 静态资源
├── src/                          # 源代码
│   ├── api/                      # API接口
│   ├── assets/                   # 资源文件
│   ├── components/               # 通用组件
│   ├── router/                   # 路由配置
│   ├── utils/                    # 工具函数
│   ├── views/                    # 页面组件
│   ├── App.vue                   # 根组件
│   └── main.js                   # 入口文件
├── .env.development              # 开发环境配置
├── .env.production               # 生产环境配置
├── index.html                    # HTML模板
├── package.json                  # 项目依赖和脚本
└── README.md                     # 项目说明文档
```
