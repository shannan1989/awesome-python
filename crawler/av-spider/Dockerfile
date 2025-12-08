# 基础镜像（alpine 更轻量化，slim 兼容性更好）
FROM docker.1ms.run/python:3.13-slim

# 避免Python生成.pyc文件，减少容器体积
ENV PYTHONDONTWRITEBYTECODE=1
# 禁用输出缓冲，让输出内容「实时刷新」到终端
ENV PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

RUN apt-get clean \
    # 关键：删除 /var/lib/apt/lists/* 减少体积
    && rm -rf /var/lib/apt/lists/* \
    # 更新 pip
    && pip install --no-cache-dir --upgrade pip \
    # pip 设置清华源
    && pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制依赖清单
COPY requirements.txt .

# 安装依赖（加清华源提速，--no-cache-dir 减少镜像体积）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
