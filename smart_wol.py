import os
import cv2
import time
import socket
import binascii
import threading
import math
import paramiko
from datetime import datetime
from ultralytics import YOLO
import mediapipe as mp
import face_recognition

# ================= 1. 环境配置区 =================
RTSP_URL = os.getenv("RTSP_URL", "rtsp://admin:ENYQIZ@192.168.0.184:554/h264/ch1/main/av_stream")
ROG_IP = os.getenv("ROG_IP", "192.168.0.100")
MAC_ADDRESS = os.getenv("MAC_ADDRESS", "30-C5-99-4F-15-6C")
WOL_COOLDOWN = 60
AWAY_TIME_LIMIT = int(os.getenv("AWAY_TIME_LIMIT", "15"))
TOLERANCE = float(os.getenv("TOLERANCE", "0.55"))  # 人脸容错率

PC_USER = os.getenv("PC_USER", "Admin")
PC_PASS = os.getenv("PC_PASS", "123456")


# ================= 2. 零延迟抽帧 =================
class VideoCaptureZeroDelay:
    def __init__(self, rtsp_url):
        self.cap = cv2.VideoCapture(rtsp_url)
        self.q = []
        self.running = True
        self.t = threading.Thread(target=self._reader, daemon=True)
        self.t.start()

    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(1)
                continue
            if len(self.q) > 0: self.q.pop(0)
            self.q.append(frame)

    def read(self):
        return (True, self.q[0]) if len(self.q) > 0 else (False, None)


# ================= 3. 网络指令中心 =================
def wake_on_lan(macaddress):
    current_hour = datetime.now().hour
    if 7 <= current_hour < 23:
        macaddress = macaddress.replace('-', '').replace(':', '')
        send_data = binascii.unhexlify('FFFFFFFFFFFF' + macaddress * 16)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(send_data, ('255.255.255.255', 9))
        sock.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 人脸鉴权通过！WOL 魔包已发送！", flush=True)
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌙 深夜模式 (23:00-07:00)，鉴权通过但限制唤醒。", flush=True)


def send_ssh_command(command_type):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=ROG_IP, username=PC_USER, password=PC_PASS, timeout=4)

        if command_type == "LOCK_PC":
            cmd = 'for /f "tokens=3" %a in (\'query session console\') do tsdiscon %a'
            client.exec_command(cmd)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔒 离座超时：已通过 SSH 强制锁死屏幕！", flush=True)

        elif command_type == "SHUTDOWN_PC":
            msg = "AI 识别到主人握拳手势，电脑将在 15 秒后关机！(输入 shutdown /a 取消)"
            cmd = f'shutdown /s /t 15 /c "{msg}"'
            client.exec_command(cmd)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 握拳指令：已下发关机通知！", flush=True)

        client.close()
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ SSH 连接失败: {e}", flush=True)


# ================= 4. 手势算法 =================
def is_fist(hand_landmarks):
    def calc_dist(p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    wrist = hand_landmarks.landmark[0]
    fingers = [(5, 8), (9, 12), (13, 16), (17, 20)]
    folded_count = 0
    for mcp_idx, tip_idx in fingers:
        if calc_dist(wrist, hand_landmarks.landmark[tip_idx]) < calc_dist(wrist, hand_landmarks.landmark[mcp_idx]):
            folded_count += 1
    return folded_count == 4


# ================= 5. 主干逻辑 (混合状态机) =================
def main():
    print("🚀 启动零信任混合双打系统 (FaceID + YOLO + MediaPipe)...", flush=True)

    # --- 1. 学习主人面部数据 ---
    try:
        print("====== 🔎 检索安全密钥 ======", flush=True)
        files = os.listdir('.')
        target_img = next(
            (f for f in files if f.lower().startswith('me.') and f.lower().endswith(('.jpg', '.jpeg', '.png'))), None)

        if not target_img:
            print("❌ 致命错误：找不到 me.jpg，无法建立安全基线！", flush=True)
            time.sleep(60);
            return

        my_image = face_recognition.load_image_file(target_img)
        master_encoding = face_recognition.face_encodings(my_image)[0]
        print(f"✅ 主人安全基线 [{target_img}] 建立成功！", flush=True)
    except Exception as e:
        print(f"❌ 照片解析失败，确保照片清晰可见单人人脸: {e}", flush=True)
        time.sleep(60);
        return

    # --- 2. 初始化 AI 模型 ---
    yolo_model = YOLO("yolov8n.pt")
    mp_hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

    stream = VideoCaptureZeroDelay(RTSP_URL)
    time.sleep(2)

    # --- 3. 状态机变量 ---
    is_master_authenticated = False  # 核心鉴权锁：是否已认证主人
    last_person_seen_time = time.time()
    last_wol_time = 0
    last_shutdown_time = 0

    frame_count = 0
    while True:
        ret, frame = stream.read()
        if not ret:
            time.sleep(0.1)
            continue

        frame_count += 1
        if frame_count % 15 != 0:
            continue

        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        current_time = time.time()

        # ---------- 模块 A：YOLO 身体雷达 ----------
        results = yolo_model.predict(source=small_frame, classes=[0], conf=0.5, verbose=False)
        person_detected = len(results[0].boxes) > 0

        if person_detected:
            # 看到人影了，不断刷新“在线时间”
            last_person_seen_time = current_time

            # 【鉴权环节】如果发现有人，但还没认证过，或者被撤销了认证
            if not is_master_authenticated:
                # 调起人脸识别扫描
                face_locations = face_recognition.face_locations(rgb_frame)
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces([master_encoding], face_encoding, tolerance=TOLERANCE)
                    if True in matches:
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🟢 身份确认：Master！授权开启！", flush=True)
                        is_master_authenticated = True

                        # 鉴权成功，发射开机信号
                        if current_time - last_wol_time > WOL_COOLDOWN:
                            wake_on_lan(MAC_ADDRESS)
                            last_wol_time = current_time
                        break  # 认证成功即刻跳出面部扫描

            # 【手势关机】仅在“已认证”的主人状态下，才允许扫描握拳手势
            if is_master_authenticated and (current_time - last_shutdown_time > 60):
                hand_results = mp_hands.process(rgb_frame)
                if hand_results.multi_hand_landmarks:
                    for hand_landmarks in hand_results.multi_hand_landmarks:
                        if is_fist(hand_landmarks):
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✊ 授权状态下检测到【握拳】！执行关机...",
                                  flush=True)
                            send_ssh_command("SHUTDOWN_PC")
                            last_shutdown_time = current_time
                            break

        else:
            # ---------- 模块 B：无影追踪 & 撤销授权 ----------
            away_duration = current_time - last_person_seen_time

            # 如果离开超过阈值，并且当前处于“已认证”状态
            if away_duration > AWAY_TIME_LIMIT and is_master_authenticated:
                print(
                    f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔴 目标丢失超 {AWAY_TIME_LIMIT} 秒！正在撤销授权并锁机...",
                    flush=True)
                send_ssh_command("LOCK_PC")
                # 核心：撤销授权！下次进来必须重新刷脸！
                is_master_authenticated = False


if __name__ == "__main__":
    main()