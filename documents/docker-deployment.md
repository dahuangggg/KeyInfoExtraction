# Docker部署说明

本文档提供关键信息提取系统的Docker部署指南。

## 前置条件

- 安装 [Docker](https://docs.docker.com/get-docker/)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)

## 快速启动

1. 克隆项目仓库（如果尚未克隆）
   ```bash
   git clone <仓库地址>
   cd KeyInfoExtraction
   ```

2. 配置环境变量（可选）
   - 在docker-compose.yml文件中可以修改数据库凭证和其他环境变量
   - **重要**：确保修改`SECRET_KEY`为一个安全的随机字符串

3. 构建并启动服务
   ```bash
   docker-compose up -d
   ```

4. 检查服务状态
   ```bash
   docker-compose ps
   ```

5. 访问API文档
   ```
   http://localhost:8000/docs
   ```

## 服务说明

### 后端API服务

- 基于Python 3.10和FastAPI构建
- 默认在8000端口提供服务
- API接口文档路径：`/docs`或`/redoc`

### 数据库服务

- PostgreSQL 14数据库
- 默认端口：5432
- 默认用户名/密码：keyinfo/keyinfo123（生产环境中请修改为强密码）

## 数据持久化

本配置使用Docker卷进行数据持久化：

- `postgres_data`：存储数据库文件
- `backend_data`：存储上传的文档和处理结果

## 测试部署

我们提供了一个测试脚本，可用于验证部署是否成功：

```bash
# 进入后端容器
docker-compose exec backend bash

# 安装测试依赖
pip install requests

# 运行测试脚本
python scripts/test_deployment.py
```

该脚本会自动测试系统的各项功能，包括：
- 健康检查
- 文档上传
- 文档列表
- 信息提取

如果一切正常，应该看到"全部通过"的结果。

## Linux服务器特别说明

在Linux服务器上部署时，有几点需要特别注意：

1. **文档处理依赖**：系统使用多种工具处理DOC/DOCX文件，包括LibreOffice、antiword等。Dockerfile已配置这些依赖，但如果遇到文档解析问题，可以在容器内检查：
   ```bash
   docker-compose exec backend python -c "from app.utils.document_processor import check_document_tools; print(check_document_tools())"
   ```

2. **目录权限**：确保数据目录有正确的权限，否则可能导致文件上传和处理失败：
   ```bash
   docker-compose exec backend chmod -R 777 /app/data
   ```

3. **中文字体**：如果处理的文档包含中文，确保容器内安装了中文字体（Dockerfile中已包含）。

4. **资源限制**：在处理大型文档时，可能需要调整容器资源限制：
   ```yaml
   # 在docker-compose.yml中添加
   backend:
     # ... 其他配置 ...
     deploy:
       resources:
         limits:
           cpus: '2'
           memory: 4G
   ```

## 常用操作

### 查看日志

```bash
# 查看后端服务日志
docker-compose logs -f backend

# 查看数据库日志
docker-compose logs -f db
```

### 停止服务

```bash
docker-compose down
```

### 重新构建服务

```bash
docker-compose build
```

### 完全重置（包括数据）

```bash
docker-compose down -v
docker-compose up -d
```

## 健康检查API

系统提供了一个健康检查API，可用于验证部署状态：

```bash
curl http://localhost:8000/api/v1/health
```

返回结果包含：
- 系统状态
- 数据库连接状态
- 可用的文档处理工具列表
- 系统信息

## 文档处理问题排查

如果出现文档处理错误，如"未找到LibreOffice"或"无法读取doc文件"：

1. 进入容器检查LibreOffice安装：
   ```bash
   docker-compose exec backend bash -c "which libreoffice && libreoffice --version"
   ```

2. 测试文档转换功能：
   ```bash
   docker-compose exec backend bash
   libreoffice --headless --convert-to txt:Text --outdir /tmp /path/to/your/document.doc
   ```

3. 确认其他文档工具可用：
   ```bash
   docker-compose exec backend bash -c "which antiword && antiword -h"
   ```

4. 检查Python文档处理库：
   ```bash
   docker-compose exec backend pip list | grep -E 'docx|textract'
   ```

5. 检查文档目录权限：
   ```bash
   docker-compose exec backend ls -la /app/data/uploads
   ```

## 注意事项

1. 在生产环境部署时，请修改所有默认密码
2. 默认配置的数据库和应用服务暴露在主机网络上，如需加强安全性，请修改端口映射配置
3. 如需添加HTTPS支持，建议使用Nginx进行反向代理

## 故障排除

1. 如果服务无法启动，请检查日志
   ```bash
   docker-compose logs
   ```

2. 如果数据库连接失败，可能需要等待数据库初始化完成
   ```bash
   # 检查数据库状态
   docker-compose exec db pg_isready
   ```

3. 检查后端服务健康状态
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

4. 重建容器并保留数据（如果配置文件有变更）
   ```bash
   docker-compose up -d --force-recreate --no-deps backend
   ``` 