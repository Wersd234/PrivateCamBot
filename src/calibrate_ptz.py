import sys
import os
import time

# 寻路魔法：找到 config 和 modules
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import config
from modules.ys_cloud import EzvizCloud


def main():
    print("=" * 50)
    print("🤖 萤石 C6CN 云台电机极限量测与初始化工具")
    print("=" * 50)

    ezviz = EzvizCloud()

    # --- 第 1 步：物理归零 ---
    print("\n[步骤 1/2] 正在向左无脑旋转，寻找物理机械原点 (绝对 0 度)...")
    print("请耐心等待大约 15 秒钟，即使它撞墙了发出咔咔声也不用管它...")
    ezviz.ptz_cmd(direction=2, action="start")  # 2是向左

    # 强制等待 15 秒，确保无论它本来在哪，都能转到最左边死角
    time.sleep(15)
    ezviz.ptz_cmd(direction=2, action="stop")
    print("✅ 已到达最左侧死角！现在这里就是 0 度！")

    # --- 第 2 步：人工测算极限时间 ---
    print("\n" + "=" * 50)
    print("[步骤 2/2] 准备测试极限转速！")
    print("请紧盯你的摄像头，准备好后在键盘上按下【回车键】开始...")
    input("👉 准备好请按回车：")

    print("\n🔄 正在狂飙向右旋转！")
    print("⚠️ 注意：当它转到最右边物理尽头（卡住不动）时，请【立刻按下回车键】刹车！！！")

    ezviz.ptz_cmd(direction=3, action="start")  # 3是向右
    start_time = time.time()

    # 等待用户敲击回车键
    input("👉 到底了请立刻按回车：")

    ezviz.ptz_cmd(direction=3, action="stop")
    end_time = time.time()

    total_time = end_time - start_time

    # --- 结算与输出 ---
    print("\n" + "=" * 50)
    print(f"🎉 测算完美结束！")
    print(f"你的 C6CN 从最左边转到最右边，总共耗时：【 {total_time:.2f} 秒 】")
    print("=" * 50)
    print("\n👇 请打开你的 src/config.py 文件，修改以下参数：")
    print(f"PTZ_360_TIME = {total_time:.2f}")

    # 顺便帮你算出角速度参考
    # 注：C6CN 的物理极限通常是左右 340 度左右，为了方便计算，我们依然按 360 这个虚拟标尺算
    deg_per_sec = 360.0 / total_time
    print(f"\n💡 (极客参考数据: 你的电机角速度大约为 {deg_per_sec:.1f} 度/秒)")


if __name__ == "__main__":
    main()