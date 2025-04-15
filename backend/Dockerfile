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

# 验证LibreOffice安装
RUN libreoffice --version || echo "LibreOffice 安装可能有问题，请检查"

# 安装Python文档处理库
RUN pip install --no-cache-dir textract python-docx docx2txt

# 复制项目文件
COPY . /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录并设置权限
RUN mkdir -p /app/data/uploads /app/data/output \
    && chmod -R 777 /app/data

# 暴露应用端口
EXPOSE 8000

# 运行应用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 