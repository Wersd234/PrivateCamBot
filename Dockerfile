# 基础镜像使用 Python 3.11 Slim
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装必要的系统底层编译环境（dlib 和 opencv 需要）
# 这里我们用完了缓存马上清理，保持镜像体积最小
RUN apt-get update && \
    apt-get install -y cmake g++ make && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖列表并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 把代码复制进容器
COPY smart_wol.py .

# 设置默认运行命令 (-u 参数保证终端实时打印日志不被缓存)
CMD ["python", "-u", "smart_wol.py"]