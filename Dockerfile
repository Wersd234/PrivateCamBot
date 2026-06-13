FROM python:3.10-slim

WORKDIR /app

# 1. 禁用安装过程中的弹窗提示，防止容器卡死
ENV DEBIAN_FRONTEND=noninteractive

# 2. 核心修复：增加 5 次网络重试，并替换为最新的 libgl1 依赖
RUN apt-get clean && \
    apt-get update -o Acquire::Retries=5 || apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    cmake \
    g++ \
    make \
    libgl1 \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "smart_wol.py"]