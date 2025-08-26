#!/usr/bin/env python3
"""
简化的健康检查脚本
定期清理超时任务
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.env_config import get_config
from core.storage import FileStorageManager

def cleanup_stuck_tasks():
    """清理卡住的任务"""
    config = get_config()
    storage = FileStorageManager(config.DATA_DIR)
    
    all_tasks = storage.get_tasks()
    now = datetime.utcnow()
    cleaned = 0
    
    for task_id, task in all_tasks['tasks'].items():
        if task.get('status') in ['queued', 'processing']:
            created_at = datetime.fromisoformat(task.get('created_at', ''))
            duration = now - created_at
            
            # 超过30分钟的任务标记为失败
            if duration > timedelta(minutes=30):
                task['status'] = 'failed'
                task['error_message'] = 'Task timeout - automatically cleaned'
                task['completed_at'] = now.isoformat()
                storage.save_task(task_id, task)
                cleaned += 1
                print(f"Cleaned stuck task: {task_id}")
    
    if cleaned == 0:
        print("No stuck tasks found")
    else:
        print(f"Cleaned {cleaned} stuck tasks")

if __name__ == '__main__':
    cleanup_stuck_tasks()