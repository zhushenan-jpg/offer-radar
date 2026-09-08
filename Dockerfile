# OfferRadar Docker 镜像
# 基于 Python 3.12 slim 镜像

FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements-lock.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements-lock.txt

# 复制项目文件
COPY pyproject.toml .
COPY src/ src/
COPY scripts/ scripts/
COPY profile.example.yaml .

# 安装项目
RUN pip install -e .

# 创建数据目录
RUN mkdir -p data logs backups

# 设置环境变量
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# 暴露 Streamlit 端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "print('OK')" || exit 1

# 默认启动命令: 启动 Streamlit 面板
CMD ["python", "-m", "streamlit", "run", "src/jobpilot/app/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
