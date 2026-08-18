FROM python:3.11-slim

WORKDIR /app

# 设置 Python 环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV STREAMLIT_SERVER_HEADLESS=true 

# 安装系统依赖（连 PostgreSQL，libpq-dev 是必须的）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 1. 核心修改：克隆整个仓库到当前 /app 目录下
RUN git clone https://github.com/sgvrstudio-pixel/cmi-platform.git .

# # 2. 使用 Linux 强行删除 src 之外的所有无关文件和文件夹
# # 利用 shopt 开启扩展通配符，保留 src 和 requirements.txt，其余全删
# RUN bash -c "shopt -s extglob && rm -rf ! (src|requirements.txt)"

# 2. 核心修改：先升级 pip，然后直接安装根目录下的 requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt 

EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 3. 核心修改：根据你的 GitHub 结构，app_v2.py 实际是在 src/ 目录下！
# 既然克隆到了 /app，那它的相对路径就是 src/app_v2.py
CMD ["streamlit", "run", "src/app_v2.py", "--server.port=8501", "--server.address=0.0.0.0"]