# 专业文档关键要素提取系统 - Docker部署指南 (SQLite版)

本文档提供使用Docker部署专业文档关键要素自动识别和提取系统的详细步骤。该版本使用SQLite作为数据库，简化了部署过程。

## 前置条件

- 安装 [Docker](https://docs.docker.com/get-docker/)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)

## 部署步骤

### 1. 准备环境

将Dockerfile、docker-compose.yml和.env文件放在正确的位置：
- Dockerfile → 放在后端项目根目录 (backend/)
- docker-compose.yml → 放在整个项目的根目录
- .env → 放在后端项目根目录 (backend/)

### 2. 配置环境变量

编辑`.env`文件，设置以下关键配置：
- 设置`LLM_API_KEY`为你的OpenAI API密钥（如果使用API模式）
- 根据需要调整其他配置项

### 3. 构建并启动服务

```bash
# 在项目根目录执行
docker-compose up -d
```

上述命令将：
- 构建后端服务镜像
- 创建必要的数据卷用于持久化数据
- 创建应用网络

### 4. 验证部署

构建完成后，检查服务是否正常运行：

```bash
# 检查服务状态
docker-compose ps

# 查看应用日志
docker-compose logs -f backend
```

应用API文档可通过以下URL访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 5. 使用健康检查API

你可以通过健康检查API验证系统是否正常运行：

```bash
curl http://localhost:8000/api/v1/health
```

## 常用操作

### 停止服务

```bash
docker-compose down
```

### 重新构建服务

```bash
docker-compose build
```

### 查看日志

```bash
# 查看后端日志
docker-compose logs -f backend
```

### 进入容器

```bash
# 进入后端容器
docker-compose exec backend bash
```

### 直接访问SQLite数据库

```bash
# 进入容器
docker-compose exec backend bash

# 访问SQLite数据库
sqlite3 /app/db/key_info_extraction.db

# 查看表结构
.tables
.schema documents
```

### 完全重置（慎用，会删除所有数据）

```bash
docker-compose down -v
docker-compose up -d
```

## 文件卷说明

系统使用Docker卷保存重要数据：
- `backend_data`: 包含上传的文档和处理结果
- `backend_db`: 包含SQLite数据库文件
- `backend_logs`: 包含应用日志

## 优势说明

使用SQLite作为数据库具有以下优势：
1. **简化部署**: 不需要单独的数据库服务
2. **易于备份**: 数据库就是单个文件，容易备份和恢复
3. **减少资源占用**: 适合小型部署和开发环境
4. **零配置**: 不需要配置数据库用户、密码等

## 问题排查

如果遇到问题，请尝试以下步骤：

1. 检查日志
   ```bash
   docker-compose logs -f backend
   ```

2. 确认数据库目录权限
   ```bash
   docker-compose exec backend ls -la /app/db
   ```

3. 验证数据库文件是否存在
   ```bash
   docker-compose exec backend ls -la /app/db/key_info_extraction.db
   ```

4. 确认数据库连接
   ```bash
   docker-compose exec backend python -c "from app.db.session import engine; print(engine.connect())"
   ```

5. 验证文档处理工具
   ```bash
   docker-compose exec backend libreoffice --version
   ```

## 安全注意事项

1. SQLite数据库文件存储在容器卷中，确保正确设置权限
2. 避免将API密钥直接写入Dockerfile或docker-compose.yml
3. 考虑配置TLS/SSL，使用Nginx或Traefik作为反向代理