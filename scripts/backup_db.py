"""数据库自动备份脚本.

功能：
1. 备份 SQLite 数据库
2. 保留最近 30 天的备份
3. 支持定时执行

使用方法：
    python scripts/backup_db.py [--db jobpilot.db] [--backup-dir backups] [--keep-days 30]
"""

import argparse
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def backup_database(db_path: str, backup_dir: str, keep_days: int = 30) -> str:
    """备份数据库.

    Args:
        db_path: 数据库文件路径
        backup_dir: 备份目录
        keep_days: 保留天数

    Returns:
        备份文件路径
    """
    db_path = Path(db_path)
    backup_dir = Path(backup_dir)

    # 创建备份目录
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"jobpilot_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    # 备份数据库
    try:
        # 使用 SQLite 的 backup API 进行热备份
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(backup_path)
        source.backup(dest)
        source.close()
        dest.close()

        print(f"✅ 备份成功: {backup_path}")
        print(f"   大小: {backup_path.stat().st_size / 1024:.2f} KB")

    except Exception as e:
        print(f"❌ 备份失败: {e}")
        raise

    # 清理旧备份
    cleanup_old_backups(backup_dir, keep_days)

    return str(backup_path)


def cleanup_old_backups(backup_dir: Path, keep_days: int) -> None:
    """清理旧备份文件.

    Args:
        backup_dir: 备份目录
        keep_days: 保留天数
    """
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    cutoff_timestamp = cutoff_date.timestamp()

    deleted_count = 0
    for backup_file in backup_dir.glob("jobpilot_*.db"):
        if backup_file.stat().st_mtime < cutoff_timestamp:
            backup_file.unlink()
            deleted_count += 1

    if deleted_count > 0:
        print(f"🗑️ 已清理 {deleted_count} 个旧备份文件")


def list_backups(backup_dir: str) -> list:
    """列出所有备份文件.

    Args:
        backup_dir: 备份目录

    Returns:
        备份文件列表
    """
    backup_dir = Path(backup_dir)
    backups = sorted(backup_dir.glob("jobpilot_*.db"), reverse=True)
    return backups


def main():
    parser = argparse.ArgumentParser(description="数据库自动备份脚本")
    parser.add_argument("--db", default="jobpilot.db", help="数据库文件路径")
    parser.add_argument("--backup-dir", default="backups", help="备份目录")
    parser.add_argument("--keep-days", type=int, default=30, help="保留天数")
    parser.add_argument("--list", action="store_true", help="列出所有备份")

    args = parser.parse_args()

    if args.list:
        backups = list_backups(args.backup_dir)
        if backups:
            print(f"📦 备份文件列表 ({len(backups)} 个):")
            for backup in backups:
                size_kb = backup.stat().st_size / 1024
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"   {backup.name} ({size_kb:.2f} KB, {mtime})")
        else:
            print("📦 暂无备份文件")
        return

    try:
        backup_path = backup_database(args.db, args.backup_dir, args.keep_days)
        print(f"\n✅ 备份完成: {backup_path}")

    except Exception as e:
        print(f"\n❌ 备份失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()
