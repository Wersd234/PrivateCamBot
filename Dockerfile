FROM python:3.10-slim

WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive

# 换国内源并安装编译环境与图形渲染库
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources || true && \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list || true && \
    apt-get clean && \
    apt-get update -o Acquire::Retries=5 || apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    cmake \
    g++ \
    make \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgles2 && \
    rm -rf /var/lib/apt/lists/*

COPY properties/requirements.txt ./properties/
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r properties/requirements.txt

COPY . .

CMD ["python", "-u", "src/main.py"]