# 1. 使用最稳定的 Python 3.10
FROM python:3.10-slim

WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive

# 2. 换国内源并安装 dlib(人脸识别) 必须的 C++ 环境
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources || true && \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list || true && \
    apt-get clean && \
    apt-get update -o Acquire::Retries=5 || apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    cmake g++ make libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# 3. 极速安装 Python 依赖库
# 注意：这里我们明确指向 properties 文件夹
COPY properties/requirements.txt ./properties/
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r properties/requirements.txt

# 4. 把你所有的文件夹 (properties, resource, src) 全复制进去
COPY . .

# 5. 启动入口
CMD ["python", "-u", "src/main.py"]