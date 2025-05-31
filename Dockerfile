FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装uv包管理器
RUN pip install uv

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY templates/ ./templates/

# 安装Python依赖
RUN uv sync --frozen

# 创建数据目录（这将是挂载点）
RUN mkdir -p /app/data

# 设置环境变量
ENV DATA_ROOT=/app/data
ENV WEB_HOST=0.0.0.0
ENV WEB_PORT=8000

# 暴露端口
EXPOSE 8000

# 创建启动脚本
RUN echo '#!/bin/bash\n\
# 初始化数据库（如果不存在）\n\
if [ ! -f "/app/data/bilibili_favorites.db" ]; then\n\
    echo "初始化数据库..."\n\
    uv run python src/cli.py init-db\n\
fi\n\
\n\
# 启动Web服务\n\
echo "启动Web服务..."\n\
uv run uvicorn src.bilibili_my_favorite.app:app --host $WEB_HOST --port $WEB_PORT\n\
' > /app/start.sh && chmod +x /app/start.sh

# 设置默认命令
CMD ["/app/start.sh"] 