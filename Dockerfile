FROM python:3.10-slim

WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive

# 【提速黑科技 1】强制开启 CPU 所有核心，疯狂加速编译 dlib！
ENV CMAKE_BUILD_PARALLEL_LEVEL=8

# 换国内源，并【补齐 libegl1 图形库】，彻底消灭 MediaPipe 的崩溃报错！
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
    libgles2 \
    libegl1 && \
    rm -rf /var/lib/apt/lists/*

COPY properties/requirements.txt ./properties/

# 【提速黑科技 2】提前截胡！强制只下载 150MB 的纯 CPU 版深度学习框架，省去 2.5GB 下载量！
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 飞速安装剩余依赖
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r properties/requirements.txt

COPY . .

CMD ["python", "-u", "src/main.py"]