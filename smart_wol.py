import os
import cv2
import face_recognition
import socket
import binascii
import time
import threading

# ================= 1. Docker 环境变量配置区 =================
RTSP_URL = os.getenv("RTSP_URL", "rtsp://admin:ENYQIZ@192.168.0.184:554/h264/ch1/main/av_stream")
MAC_ADDRESS = os.getenv("MAC_ADDRESS", "d4:b7:61:75:64:59")
WOL_COOLDOWN = int(os.getenv("WOL_COOLDOWN", "60"))
TOLERANCE = float(os.getenv("TOLERANCE", "0.6"))  # 容错率，数值越大越容易识别


# ================= 2. 零延迟 RTSP 读取流 (多线程) =================
class VideoCaptureZeroDelay:
    def __init__(self, rtsp_url):
        self.cap = cv2.VideoCapture(rtsp_url)
        self.q = []
        self.running = True
        # 开启后台线程疯狂抽帧
        self.t = threading.Thread(target=self._reader)
        self.t.daemon = True
        self.t.start()

    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(1)  # 断线缓冲
                continue
            # 队列里只保留绝对的“最新一帧”，旧的直接扔掉
            if len(self.q) > 0:
                self.q.pop(0)
            self.q.append(frame)

    def read(self):
        if len(self.q) == 0:
            return False, None
        return True, self.q[0]

    def release(self):
        self.running = False
        self.cap.release()


# ================= 3. WOL 发送函数 =================
def wake_on_lan(macaddress):
    macaddress = macaddress.replace('-', '').replace(':', '')
    send_data = binascii.unhexlify('FFFFFFFFFFFF' + macaddress * 16)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(send_data, ('255.255.255.255', 9))
    sock.close()
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🚀 WOL 唤醒魔包已广播，目标: {MAC_ADDRESS}", flush=True)


# ================= 4. 主干逻辑 =================
def main():
    print(f"🔄 启动 AI-WOL 守护进程... 目标 MAC: {MAC_ADDRESS}", flush=True)

    # ===== 新增透视代码 =====
    print("====== 🔎 Docker 内部文件侦探 ======", flush=True)
    print(f"当前工作目录: {os.getcwd()}", flush=True)
    print(f"目录下的所有文件: {os.listdir('.')}", flush=True)
    print("====================================", flush=True)
    # ========================


    # 学习人脸
    try:
        my_image = face_recognition.load_image_file("me.jpg")
        my_face_encoding = face_recognition.face_encodings(my_image)[0]
        print("✅ 人脸底片学习成功！", flush=True)
    except Exception as e:
        print(f"❌ 读取 me.jpg 失败，请检查文件是否存在或人脸是否清晰！报错: {e}", flush=True)
        return

    known_encodings = [my_face_encoding]
    last_wol_time = 0

    print("📡 正在连接 RTSP 流...", flush=True)
    stream = VideoCaptureZeroDelay(RTSP_URL)

    # 给线程 2 秒钟时间连接并拉取第一帧
    time.sleep(2)
    print("🛡️ 系统已就绪，开始实时监测...", flush=True)

    # 跳帧计数器，不需要每帧都算，1秒算2~3次就足够了
    frame_count = 0

    while True:
        ret, frame = stream.read()
        if not ret:
            time.sleep(0.1)
            continue

        frame_count += 1
        # 每处理 1 帧，跳过中间的 10 帧 (极大降低 CPU 负担，反正是固定镜头)
        if frame_count % 10 != 0:
            continue

        # 缩小画面加速计算 (缩小2倍)
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # 找人脸并编码
        face_locations = face_recognition.face_locations(rgb_small_frame)
        if not face_locations:
            continue  # 没看到脸就直接跳过

        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=TOLERANCE)

            if True in matches:
                current_time = time.time()
                # 检查冷却时间
                if current_time - last_wol_time > WOL_COOLDOWN:
                    print(f"[{time.strftime('%H:%M:%S')}] 💡 发现主人！正在触发开机...", flush=True)
                    wake_on_lan(MAC_ADDRESS)
                    last_wol_time = current_time


if __name__ == "__main__":
    main()