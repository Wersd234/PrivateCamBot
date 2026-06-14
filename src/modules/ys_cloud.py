import os, time, json, requests, threading
import config


class EzvizCloud:
    def __init__(self):
        self.cache_file = config.TOKEN_CACHE_PATH
        self.ptz_busy = False

        # --- 虚拟惯导系统核心变量 ---
        self.current_angle = 0.0  # 当前预估角度
        self.ptz_360_time = getattr(config, 'PTZ_360_TIME', 15.0)
        self.deg_per_sec = 360.0 / self.ptz_360_time  # 角速度 (度/秒)
        self.move_start_time = 0
        self.moving_dir = None

    def get_token(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if int(time.time() * 1000) < (data.get("expireTime", 0) - 600000):
                        return data.get("accessToken")
            except:
                pass

        print("🔄 正在向萤石云获取新 Token...", flush=True)
        try:
            res = requests.post("https://open.ys7.com/api/lapp/token/get",
                                data={"appKey": config.YS_APP_KEY, "appSecret": config.YS_APP_SECRET}, timeout=5).json()
            if res.get("code") == "200":
                with open(self.cache_file, 'w', encoding='utf-8') as f: json.dump(res["data"], f)
                return res["data"]["accessToken"]
        except:
            pass
        return None

    def ptz_cmd(self, direction, action):
        """发送指令，并实时记录时间推算当前绝对角度"""
        token = self.get_token()
        if not token: return
        payload = {"accessToken": token, "deviceSerial": config.YS_DEVICE_SERIAL, "channelNo": config.CHANNEL_NO,
                   "direction": direction, "speed": 1}

        try:
            requests.post(f"https://open.ys7.com/api/lapp/device/ptz/{action}", data=payload, timeout=3)
            now = time.time()

            # --- 航位推算法：计算角度偏移 ---
            if action == "start":
                self.move_start_time = now
                self.moving_dir = direction
            elif action == "stop" and self.moving_dir:
                dt = now - self.move_start_time
                delta_angle = dt * self.deg_per_sec
                if self.moving_dir == 2:  # 2 是向左
                    self.current_angle = max(0.0, self.current_angle - delta_angle)
                elif self.moving_dir == 3:  # 3 是向右
                    self.current_angle = min(360.0, self.current_angle + delta_angle)
                self.moving_dir = None
                print(f"📐 [导航雷达] 当前预估绝对角度: {self.current_angle:.1f}°", flush=True)
        except:
            pass

    def goto_angle(self, target_angle):
        """让云台转到任意绝对角度"""
        self.ptz_busy = True
        diff = target_angle - self.current_angle

        # 误差在 5 度以内忽略，防止微小抽搐
        if abs(diff) < 5.0:
            self.ptz_busy = False
            return

        direction = 3 if diff > 0 else 2  # 差值为正向右转，负向左转
        move_time = abs(diff) / self.deg_per_sec

        print(f"🤖 [PTZ] 正在前往 {target_angle}° (预计耗时 {move_time:.1f}s)...", flush=True)
        self.ptz_cmd(direction, "start")
        time.sleep(move_time)
        self.ptz_cmd(direction, "stop")

        self.current_angle = target_angle
        self.ptz_busy = False

    def calibrate_home(self):
        """物理级撞墙归零校准"""
        self.ptz_busy = True
        print("🤖 [PTZ] 正在执行硬归零校准 (寻找物理0度)...", flush=True)
        self.ptz_cmd(2, "start")
        time.sleep(self.ptz_360_time)
        self.ptz_cmd(2, "stop")
        self.current_angle = 0.0  # 绝对校准为 0 度
        print("🤖 [PTZ] 归零完毕！", flush=True)
        self.ptz_busy = False

    def goto_angle_async(self, target_angle):
        threading.Thread(target=self.goto_angle, args=(target_angle,), daemon=True).start()

    def calibrate_and_goto_work_async(self):
        """开机流程：先归零找原点，再前往电脑椅工作位"""

        def routine():
            self.calibrate_home()
            work_angle = getattr(config, 'ANGLE_WORK', 120)
            self.goto_angle(work_angle)

        threading.Thread(target=routine, daemon=True).start()