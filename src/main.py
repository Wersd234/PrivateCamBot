import sys
import os
import time
import cv2
import threading
import urllib.request
import math
from datetime import datetime

# ================= 终极防弹寻路魔法 =================
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import config
from modules.hw_control import wake_on_lan, send_ssh_lock, send_ssh_command
from modules.camera_ai import AIVisionEngine

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ================= 手势算法 =================
def calc_dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


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


# ================= 主干神经 =================
def main():
    print("🚀 启动 [Docker后台极速版] 静默 AI 哨兵矩阵...", flush=True)

    # 1. 自动下载最新的手部模型
    MODEL_PATH = os.path.join(config.ROOT_DIR, "properties", "hand_landmarker.task")
    if not os.path.exists(MODEL_PATH):
        print("🔄 正在从 Google 下载手部模型...", flush=True)
        urllib.request.urlretrieve(
            "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            MODEL_PATH)

    # 2. 初始化 AI 引擎
    try:
        ai_engine = AIVisionEngine()
        print("✅ 视觉引擎初始化成功！", flush=True)
    except Exception as e:
        print(f"❌ 引擎初始化失败: {e}", flush=True)
        return

    # 3. 初始化 MediaPipe 手部雷达
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1, min_hand_detection_confidence=0.4)
    hand_detector = vision.HandLandmarker.create_from_options(options)

    # 4. 状态机变量
    is_master_auth = False
    last_person_seen_time = time.time()
    last_wol_time = 0
    frame_count = 0
    fist_hold_frames = 0
    shutdown_pending = False

    # 【新增】3 小时健康心跳时间戳
    last_health_check = time.time()

    print("🛡️ 系统已进入 24 小时无人值守警戒模式！", flush=True)

    while True:
        ret, frame = ai_engine.get_frame()
        if not ret:
            time.sleep(0.1)
            continue

        frame_count += 1
        # 后台运行 15 帧处理一次，极致节省 CPU 算力
        if frame_count % 15 != 0:
            continue

        current_time = time.time()

        # 【新增】每 3 小时 (10800秒) 定时汇报心跳
        if current_time - last_health_check >= 10800:
            print(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] 💓 [健康心跳] 系统已稳定值守 3 小时，网络链接与 AI 引擎完美运行中！",
                flush=True)
            last_health_check = current_time

        # 缩小一半送给 AI，加快处理速度
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # ---------- 模块 A：防偷窥身体雷达 ----------
        person_detected = ai_engine.detect_person(small_frame)

        if person_detected:
            # 只要看到人，就刷新在线时间
            last_person_seen_time = current_time

            # 【首次入座鉴权】
            if not is_master_auth:
                if ai_engine.verify_master(small_frame, config.TOLERANCE):
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🟢 身份确认：Master！授权开启。", flush=True)
                    is_master_auth = True
                    # 发送 WOL 唤醒电脑
                    if current_time - last_wol_time > config.WOL_COOLDOWN:
                        wake_on_lan()
                        last_wol_time = current_time

            # 【授权状态下的手势控制】
            if is_master_auth:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                detection_result = hand_detector.detect(mp_image)

                if detection_result.hand_landmarks:
                    hand_landmarks = detection_result.hand_landmarks[0]

                    # 动作 1：握拳关机
                    if is_fist(hand_landmarks):
                        fist_hold_frames += 1
                        # 后台帧率低，连续 3 帧即代表 1.5 秒蓄力完成，防误触
                        if fist_hold_frames >= 3 and not shutdown_pending:
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✊ 确认连续握拳！下发 60 秒关机倒计时...",
                                  flush=True)
                            threading.Thread(target=send_ssh_command, args=("SHUTDOWN_PC",), daemon=True).start()
                            shutdown_pending = True
                            fist_hold_frames = 0
                            is_master_auth = False  # 关机后自动撤销授权

                    # 动作 2：张手取消关机
                    elif is_open_hand(hand_landmarks):
                        fist_hold_frames = 0
                        if shutdown_pending:
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✋ 张开手掌！正在撤销关机指令...",
                                  flush=True)
                            threading.Thread(target=send_ssh_command, args=("CANCEL_SHUTDOWN",), daemon=True).start()
                            shutdown_pending = False

                    else:
                        # 手势不标准，蓄力清零
                        fist_hold_frames = 0
                else:
                    fist_hold_frames = 0
        else:
            # 画面里没人，蓄力清零
            fist_hold_frames = 0

            # ---------- 模块 B：离座撤销授权与锁屏 ----------
            if is_master_auth:
                away_duration = current_time - last_person_seen_time
                if away_duration > config.AWAY_TIME_LIMIT:
                    print(
                        f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔴 目标丢失超 {config.AWAY_TIME_LIMIT} 秒！执行安全锁屏...",
                        flush=True)
                    send_ssh_lock()
                    is_master_auth = False
                    shutdown_pending = False


if __name__ == "__main__":
    main()