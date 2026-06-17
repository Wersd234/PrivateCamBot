import os
import cv2
import time
import threading
import face_recognition
from ultralytics import YOLO
import config


class AIVisionEngine:
    def __init__(self):
        self.yolo_model = YOLO(config.YOLO_MODEL_PATH)

        self.master_encodings = []
        face_dir = os.path.join(config.ROOT_DIR, "resource", "master_faces")
        for file in os.listdir(face_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                img = face_recognition.load_image_file(os.path.join(face_dir, file))
                encodings = face_recognition.face_encodings(img)
                if len(encodings) > 0:
                    self.master_encodings.append(encodings[0])

        if len(self.master_encodings) == 0:
            raise FileNotFoundError("致命错误：没有任何有效的主人照片！")

        # 记录 RTSP 地址，方便断线时重连
        self.rtsp_url = config.RTSP_URL
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.q = []
        self.running = True
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                # 【新增：军工级断线重连看门狗】
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ 警告：RTSP 视频流中断！3秒后尝试重新连接...", flush=True)
                self.cap.release()
                time.sleep(3)
                self.cap = cv2.VideoCapture(self.rtsp_url)
                continue

            if len(self.q) > 0: self.q.pop(0)
            self.q.append(frame)

    def get_frame(self):
        return (True, self.q[0]) if len(self.q) > 0 else (False, None)

    def detect_person(self, frame):
        results = self.yolo_model.predict(source=frame, classes=[0], conf=0.3, verbose=False)
        return len(results[0].boxes) > 0

    def verify_master(self, frame, tolerance):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        for face_encoding in face_encodings:
            if True in face_recognition.compare_faces(self.master_encodings, face_encoding, tolerance=tolerance):
                return True
        return False