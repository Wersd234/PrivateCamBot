import cv2, time, threading
import face_recognition
from ultralytics import YOLO
import config


class AIVisionEngine:
    def __init__(self):
        self.yolo_model = YOLO(config.YOLO_MODEL_PATH)
        my_image = face_recognition.load_image_file(config.ME_JPG_PATH)
        self.master_encoding = face_recognition.face_encodings(my_image)[0]

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
        """只返回画面中是否有人，剔除云台坐标计算"""
        results = self.yolo_model.predict(source=frame, classes=[0], conf=0.3, verbose=False)
        return len(results[0].boxes) > 0

    def verify_master(self, frame, tolerance):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        for face_encoding in face_encodings:
            if True in face_recognition.compare_faces([self.master_encoding], face_encoding, tolerance=tolerance):
                return True
        return False