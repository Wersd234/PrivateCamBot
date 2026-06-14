import os
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, "properties", ".env")
load_dotenv(dotenv_path=ENV_PATH)

# ================= 核心硬件与网络配置 =================
RTSP_URL = os.getenv("RTSP_URL", "rtsp://admin:ENYQIZ@192.168.0.184:554/h264/ch1/main/av_stream")
ROG_IP = os.getenv("ROG_IP", "192.168.0.100")
MAC_ADDRESS = os.getenv("MAC_ADDRESS", "30-C5-99-4F-15-6C")
PC_USER = os.getenv("PC_USER", "Admin")
PC_PASS = os.getenv("PC_PASS", "123456")

# ================= 状态机控制参数 =================
AWAY_TIME_LIMIT = int(os.getenv("AWAY_TIME_LIMIT", "15"))
TOLERANCE = float(os.getenv("TOLERANCE", "0.55"))
WOL_COOLDOWN = 60

# ================= 资源绝对路径 =================
ME_JPG_PATH = os.path.join(ROOT_DIR, "resource", "me.jpg")
YOLO_MODEL_PATH = os.path.join(ROOT_DIR, "properties", "yolov8n.pt")