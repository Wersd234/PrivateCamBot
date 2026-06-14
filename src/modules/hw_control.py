import socket
import binascii
import paramiko
from datetime import datetime
import config


def wake_on_lan():
    if 7 <= datetime.now().hour < 23:
        mac = config.MAC_ADDRESS.replace('-', '').replace(':', '')
        send_data = binascii.unhexlify('FFFFFFFFFFFF' + mac * 16)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(send_data, ('255.255.255.255', 9))
        sock.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 WOL 唤醒魔包已发送！", flush=True)
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌙 深夜模式，限制自动唤醒。", flush=True)


def send_ssh_command(command_type):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=config.ROG_IP, username=config.PC_USER, password=config.PC_PASS, timeout=5)

        if command_type == "LOCK_PC":
            magic_cmd = 'powershell -Command "$sessions = Get-Process -Name explorer -ErrorAction SilentlyContinue | Select-Object -ExpandProperty SessionId -Unique; foreach ($s in $sessions) { tsdiscon $s }"'
            client.exec_command(magic_cmd)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔒 离座锁定：已通过 SSH 强制锁屏！", flush=True)

        elif command_type == "SHUTDOWN_PC":
            # 60 秒倒计时关机
            msg = "AI 识别到握拳，60 秒后关机！(对镜头【张开手掌 ✋】即可取消)"
            cmd = f'shutdown /s /t 60 /c "{msg}"'
            client.exec_command(cmd)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 握拳关机：已下发 60 秒倒计时关机指令！", flush=True)

        elif command_type == "CANCEL_SHUTDOWN":
            # 撤销关机
            client.exec_command('shutdown /a')
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✋ 张手识别成功：已撤销关机！", flush=True)

        client.close()
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ SSH 操作失败: {e}", flush=True)


def send_ssh_lock():
    send_ssh_command("LOCK_PC")