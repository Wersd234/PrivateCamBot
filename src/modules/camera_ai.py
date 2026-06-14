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

        # ================= 黄金级优化：多模态特征池 =================
        self.master_encodings = []
        face_dir = os.path.join(config.ROOT_DIR, "resource", "master_faces")

        if not os.path.exists(face_dir):
            os.makedirs(face_dir)

        print("====== 🔎 检索多模态安全特征池 ======", flush=True)
        for file in os.listdir(face_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(face_dir, file)
                try:
                    img = face_recognition.load_image_file(img_path)
                    encodings = face_recognition.face_encodings(img)
                    if len(encodings) > 0:
                        self.master_encodings.append(encodings[0])
                        print(f"✅ 成功加载授权基线: [{file}]", flush=True)
                    else:
                        print(f"⚠️ 警告: 照片 [{file}] 中未检测到清晰人脸，已跳过。", flush=True)
                except Exception as e:
                    print(f"❌ 读取照片 [{file}] 失败: {e}", flush=True)

        if len(self.master_encodings) == 0:
            raise FileNotFoundError(f"致命错误：{face_dir} 目录下没有任何有效的主人照片！")
        print("====================================", flush=True)
        # ==========================================================

        self.cap = cv2.VideoCapture(config.RTSP_URL)
        self.q = []
        self.running = True
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret: time.sleep(1); continue
            if len(self.q) > 0: self.q.pop(0)
            self.q.append(frame)

    def get_frame(self):
        return (True, self.q[0]) if len(self.q) > 0 else (False, None)

    def detect_person(self, frame):
        """YOLO 身体雷达"""
        results = self.yolo_model.predict(source=frame, classes=[0], conf=0.3, verbose=False)
        return len(results[0].boxes) > 0

    def verify_master(self, frame, tolerance):
        """黄金级多模态鉴权"""
        # 注意：这里我们不用 small_frame，直接用原图 frame 保证清晰度！
        # 因为只有在需要鉴权的那一瞬间才会执行这里，平时不执行，所以绝不卡顿！
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding in face_encodings:
            # 只要当前脸和特征池里的【任意一张】照片匹配成功，就算授权通过！
            matches = face_recognition.compare_faces(self.master_encodings, face_encoding, tolerance=tolerance)
            if True in matches:
                return True
        return False