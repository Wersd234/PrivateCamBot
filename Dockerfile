FROM python:3.11-slim

WORKDIR /app

# 安装必要的系统底层编译环境与图形库
RUN apt-get update && \
    apt-get install -y cmake g++ make libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 把代码和 me.jpg 统统放进去
COPY . .

CMD ["python", "-u", "smart_wol.py"]