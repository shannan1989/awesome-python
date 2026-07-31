# 基础镜像（alpine 更轻量化，slim 兼容性更好）
FROM docker.1ms.run/python:3.14-slim

# 避免Python生成.pyc文件，减少容器体积
ENV PYTHONDONTWRITEBYTECODE=1
# 禁用输出缓冲，让输出内容「实时刷新」到终端
ENV PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

# 使用清华 Debian 镜像源安装 Chromium 和对应驱动
RUN sed -i \
        's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 显式指定浏览器和驱动，避免 Selenium Manager 不支持 Linux ARM64
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# 复制依赖清单
COPY requirements.txt .

# 安装依赖（加清华源提速，--no-cache-dir 减少镜像体积）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
