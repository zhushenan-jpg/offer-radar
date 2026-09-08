"""定时备份调度脚本.

功能：
1. 每日自动备份数据库
2. 保留最近 30 天的备份
3. 支持 Windows 任务计划程序

使用方法：
    python scripts/schedule_backup.py --install  # 安装定时任务
    python scripts/schedule_backup.py --uninstall  # 卸载定时任务
    python scripts/schedule_backup.py --run  # 立即执行备份
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_python_path() -> str:
    """获取 Python 解释器路径."""
    return sys.executable


def get_script_path() -> str:
    """获取备份脚本路径."""
    return str(Path(__file__).parent / "backup_db.py")


def install_scheduled_task():
    """安装 Windows 定时任务."""
    python_path = get_python_path()
    script_path = get_script_path()

    # 创建任务计划程序命令
    task_name = "OfferRadar_Daily_Backup"
    task_command = f'schtasks /create /tn "{task_name}" /tr "{python_path} {script_path}" /sc daily /st 03:00 /f'

    try:
        result = subprocess.run(task_command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 定时任务安装成功")
            print(f"   任务名称: {task_name}")
            print(f"   执行时间: 每天 03:00")
            print(f"   执行命令: {python_path} {script_path}")
        else:
            print(f"❌ 定时任务安装失败: {result.stderr}")

    except Exception as e:
        print(f"❌ 安装失败: {e}")


def uninstall_scheduled_task():
    """卸载 Windows 定时任务."""
    task_name = "OfferRadar_Daily_Backup"
    task_command = f'schtasks /delete /tn "{task_name}" /f'

    try:
        result = subprocess.run(task_command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 定时任务卸载成功")
        else:
            print(f"❌ 定时任务卸载失败: {result.stderr}")

    except Exception as e:
        print(f"❌ 卸载失败: {e}")


def run_backup():
    """立即执行备份."""
    python_path = get_python_path()
    script_path = get_script_path()

    try:
        result = subprocess.run([python_path, script_path], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

    except Exception as e:
        print(f"❌ 执行失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="定时备份调度脚本")
    parser.add_argument("--install", action="store_true", help="安装定时任务")
    parser.add_argument("--uninstall", action="store_true", help="卸载定时任务")
    parser.add_argument("--run", action="store_true", help="立即执行备份")

    args = parser.parse_args()

    if args.install:
        install_scheduled_task()
    elif args.uninstall:
        uninstall_scheduled_task()
    elif args.run:
        run_backup()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
