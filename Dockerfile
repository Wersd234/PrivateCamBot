FROM python:3.10-slim

WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive

# 替换阿里源与安装 C++ 环境
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources || true && \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list || true && \
    apt-get clean && \
    apt-get update -o Acquire::Retries=5 || apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    cmake g++ make libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# 从 properties 文件夹复制依赖并安装
COPY properties/requirements.txt ./properties/
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r properties/requirements.txt

# 复制整个项目高级文件树
COPY . .

# 启动 src 目录下的主程序
CMD ["python", "-u", "src/main.py"]