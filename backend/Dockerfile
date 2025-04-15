FROM python:3.10-slim

WORKDIR /app

# 设置Python环境
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 安装系统依赖和文档处理工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    # LibreOffice完整安装
    libreoffice \
    libreoffice-writer \
    # 文档处理相关依赖
    antiword \
    poppler-utils \
    tesseract-ocr \
    # 解决中文字体问题
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    # 其他系统工具
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 设置LibreOffice路径
ENV PATH="/usr/lib/libreoffice/program:${PATH}"

# 创建必要的目录
RUN mkdir -p /app/data/uploads /app/data/output /app/logs

# 首先复制依赖文件，利用Docker缓存
COPY requirements.txt /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . /app/

# 设置目录权限
RUN chmod -R 777 /app/data /app/logs

# 暴露应用端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 设置启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]