import sys, os, time, cv2, threading, urllib.request, math
from datetime import datetime

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path: sys.path.insert(0, SRC_DIR)

import config
from modules.hw_control import wake_on_lan, send_ssh_lock, send_ssh_command
from modules.camera_ai import AIVisionEngine

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


def calc_dist(p1, p2): return math.hypot(p1.x - p2.x, p1.y - p2.y)


def is_fist(hand_landmarks):
    wrist = hand_landmarks[0]
    fingers = [(5, 8), (9, 12), (13, 16), (17, 20)]
    return sum(
        1 for mcp, tip in fingers if calc_dist(wrist, hand_landmarks[tip]) < calc_dist(wrist, hand_landmarks[mcp])) == 4


def is_open_hand(hand_landmarks):
    wrist = hand_landmarks[0]
    fingers = [(5, 8), (9, 12), (13, 16), (17, 20)]
    return sum(
        1 for mcp, tip in fingers if calc_dist(wrist, hand_landmarks[tip]) > calc_dist(wrist, hand_landmarks[mcp])) == 4


def main():
    print("🚀 启动 [UI可视化版] 静默 AI 哨兵...", flush=True)

    MODEL_PATH = os.path.join(config.ROOT_DIR, "properties", "hand_landmarker.task")
    if not os.path.exists(MODEL_PATH):
        urllib.request.urlretrieve(
            "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            MODEL_PATH)

    try:
        ai_engine = AIVisionEngine()
    except Exception as e:
        print(f"❌ 引擎初始化失败: {e}", flush=True); return

    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1, min_hand_detection_confidence=0.4)
    hand_detector = vision.HandLandmarker.create_from_options(options)

    is_master_auth = False
    last_person_seen_time = time.time()
    last_wol_time = 0
    frame_count = 0
    fist_hold_frames = 0
    shutdown_pending = False

    while True:
        ret, frame = ai_engine.get_frame()
        if not ret: time.sleep(0.1); continue

        frame_count += 1
        if frame_count % 3 != 0: continue

        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        current_time = time.time()

        ui_status, ui_color, ui_action = "Scanning...", (0, 255, 255), "Observer: Active"

        person_detected = ai_engine.detect_person(small_frame)

        if person_detected:
            last_person_seen_time = current_time

            if not is_master_auth:
                ui_status = "Verifying Identity..."
                if ai_engine.verify_master(frame, config.TOLERANCE):
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🟢 身份确认：Master！", flush=True)
                    is_master_auth = True
                    if current_time - last_wol_time > config.WOL_COOLDOWN:
                        wake_on_lan()
                        last_wol_time = current_time

            if is_master_auth:
                ui_status, ui_color = "Auth: MASTER", (0, 255, 0)
                if shutdown_pending: ui_status, ui_color = "SHUTDOWN IN 60s!", (0, 0, 255)

                # --- 手势防抖系统 ---
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                detection_result = hand_detector.detect(mp_image)

                if detection_result.hand_landmarks:
                    hand_landmarks = detection_result.hand_landmarks[0]
                    if is_fist(hand_landmarks):
                        fist_hold_frames += 1
                        ui_action = f"Gesture: FIST HOLDING... {fist_hold_frames}/10"
                        if fist_hold_frames >= 10 and not shutdown_pending:
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✊ 确认连续握拳！执行关机...", flush=True)
                            threading.Thread(target=send_ssh_command, args=("SHUTDOWN_PC",), daemon=True).start()
                            shutdown_pending = True
                            fist_hold_frames = 0
                            is_master_auth = False  # 关机后自动撤销授权
                    elif is_open_hand(hand_landmarks):
                        fist_hold_frames = 0
                        ui_action = "Gesture: OPEN HAND"
                        if shutdown_pending:
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✋ 张手！撤销关机指令...", flush=True)
                            threading.Thread(target=send_ssh_command, args=("CANCEL_SHUTDOWN",), daemon=True).start()
                            shutdown_pending = False
                    else:
                        fist_hold_frames = 0
                        ui_action = "Gesture: Unknown"
                else:
                    fist_hold_frames = 0
        else:
            fist_hold_frames = 0
            if is_master_auth:
                away_duration = current_time - last_person_seen_time
                ui_status, ui_color = f"AWAY: {int(away_duration)}s / {config.AWAY_TIME_LIMIT}s", (0, 165, 255)

                if away_duration > config.AWAY_TIME_LIMIT:
                    print(
                        f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔴 目标丢失超 {config.AWAY_TIME_LIMIT} 秒！执行锁屏...",
                        flush=True)
                    send_ssh_lock()
                    is_master_auth = False
                    shutdown_pending = False
            else:
                ui_status, ui_color = "Locked (Unauthenticated)", (0, 0, 255)

        # ==== 渲染 UI ====
        display_frame = cv2.resize(frame, (960, 540))
        overlay = display_frame.copy()
        cv2.rectangle(overlay, (10, 10), (450, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, display_frame, 0.4, 0, display_frame)
        cv2.putText(display_frame, "[ AI GUARDIAN STATIC V1.0 ]", (20, 40), cv2.FONT_HERSHEY_DUPLEX, 0.7,
                    (255, 255, 255), 1)
        cv2.putText(display_frame, ui_status, (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, ui_color, 2)
        cv2.putText(display_frame, ui_action, (20, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow("ROG Cyber Guardian HUD", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()