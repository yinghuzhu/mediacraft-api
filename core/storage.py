"""
文件存储管理器
基于JSON文件的轻量级数据存储系统
"""
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class FileStorageManager:
    """文件存储管理器 - 管理JSON文件的读写操作"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.sessions_file = os.path.join(data_dir, "sessions.json")
        self.tasks_file = os.path.join(data_dir, "tasks.json")
        self.users_file = os.path.join(data_dir, "users.json")
        self.config_file = os.path.join(data_dir, "config.json")
        
        # 线程锁确保文件操作的原子性
        self._lock = threading.RLock()
        
        # 确保目录和文件存在
        self._ensure_data_structure()
        
    def _ensure_data_structure(self):
        """确保数据目录和文件结构存在"""
        try:
            # 创建必要的目录
            os.makedirs(self.data_dir, exist_ok=True)
            os.makedirs(os.path.join(self.data_dir, "uploads"), exist_ok=True)
            os.makedirs(os.path.join(self.data_dir, "results"), exist_ok=True)
            
            # 确保JSON文件存在
            self._ensure_json_file(self.sessions_file, {"sessions": {}})
            self._ensure_json_file(self.tasks_file, {"tasks": {}})
            self._ensure_json_file(self.users_file, {"users": {}})
            self._ensure_json_file(self.config_file, self._get_default_config())
            
        except Exception as e:
            logger.error(f"Failed to ensure data structure: {e}")
            raise
    
    def _ensure_json_file(self, file_path: str, default_data: Dict):
        """确保JSON文件存在，如果不存在则创建默认内容"""
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump(default_data, f, indent=2)
    
    def get_tasks_dir(self) -> str:
        """获取任务存储目录"""
        tasks_dir = os.path.join(self.data_dir, "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        return tasks_dir
    
    def delete_task(self, task_id: str):
        """删除任务"""
        try:
            with self._lock:
                # 从任务文件中删除
                tasks_data = self._load_json(self.tasks_file, {"tasks": {}})
                if task_id in tasks_data["tasks"]:
                    del tasks_data["tasks"][task_id]
                    self._save_json(self.tasks_file, tasks_data)
                
                # 删除单独的任务文件（如果存在）
                task_file = os.path.join(self.get_tasks_dir(), f"{task_id}.json")
                if os.path.exists(task_file):
                    os.remove(task_file)
                    
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Failed to create JSON file {file_path}: {e}")
                raise
    
    def _get_default_config(self) -> Dict:
        """获取默认系统配置"""
        return {
            "max_concurrent_tasks": 3,
            "task_retention_days": 7,
            "max_queue_size": 50,
            "session_timeout_days": 30,
            "upload_max_size": 104857600,
            "allowed_file_types": [".mp4", ".avi", ".mov", ".mkv"],
            "system_name": "MediaCraft异步任务系统",
            "version": "1.0.0"
        }
    
    def _load_json(self, file_path: str, default: Dict) -> Dict:
        """安全加载JSON文件"""
        if not os.path.exists(file_path):
            return default
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else default
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load JSON file {file_path}: {e}, using default")
            return default
    
    def _save_json(self, file_path: str, data: Dict):
        """安全保存JSON文件"""
        try:
            # 先写入临时文件，然后原子性替换
            temp_file = file_path + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 原子性替换
            if os.name == 'nt':  # Windows
                if os.path.exists(file_path):
                    os.remove(file_path)
            os.rename(temp_file, file_path)
            
        except Exception as e:
            logger.error(f"Failed to save JSON file {file_path}: {e}")
            # 清理临时文件
            temp_file = file_path + '.tmp'
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            raise
    
    # 会话管理方法
    def get_sessions(self) -> Dict:
        """获取所有会话数据"""
        with self._lock:
            return self._load_json(self.sessions_file, {"sessions": {}})
    
    def get_session(self, sid: str) -> Optional[Dict]:
        """获取单个会话数据"""
        sessions = self.get_sessions()
        return sessions["sessions"].get(sid)
    
    def save_session(self, sid: str, session_data: Dict):
        """保存会话数据"""
        with self._lock:
            sessions = self.get_sessions()
            sessions["sessions"][sid] = session_data
            self._save_json(self.sessions_file, sessions)
    
    def delete_session(self, sid: str) -> bool:
        """删除会话数据"""
        with self._lock:
            sessions = self.get_sessions()
            if sid in sessions["sessions"]:
                del sessions["sessions"][sid]
                self._save_json(self.sessions_file, sessions)
                return True
            return False
    
    # 任务管理方法
    def get_tasks(self) -> Dict:
        """获取所有任务数据"""
        with self._lock:
            return self._load_json(self.tasks_file, {"tasks": {}})
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取单个任务数据"""
        tasks = self.get_tasks()
        return tasks["tasks"].get(task_id)
    
    def save_task(self, task_id: str, task_data: Dict):
        """保存任务数据"""
        with self._lock:
            tasks = self.get_tasks()
            tasks["tasks"][task_id] = task_data
            self._save_json(self.tasks_file, tasks)
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务数据"""
        with self._lock:
            tasks = self.get_tasks()
            if task_id in tasks["tasks"]:
                del tasks["tasks"][task_id]
                self._save_json(self.tasks_file, tasks)
                return True
            return False
    
    def get_user_tasks(self, sid: str) -> List[Dict]:
        """获取用户的所有任务"""
        tasks = self.get_tasks()
        user_tasks = []
        for task in tasks["tasks"].values():
            if task.get("sid") == sid:
                user_tasks.append(task)
        
        # 按创建时间倒序排列
        return sorted(user_tasks, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def get_tasks_by_status(self, status: str) -> List[Dict]:
        """根据状态获取任务"""
        tasks = self.get_tasks()
        return [task for task in tasks["tasks"].values() if task.get("status") == status]
    
    # 配置管理方法
    def get_config(self) -> Dict:
        """获取系统配置"""
        with self._lock:
            return self._load_json(self.config_file, self._get_default_config())
    
    def save_config(self, config: Dict):
        """保存系统配置"""
        with self._lock:
            self._save_json(self.config_file, config)
    
    def get_config_value(self, key: str, default=None):
        """获取单个配置值"""
        config = self.get_config()
        return config.get(key, default)
    
    def set_config_value(self, key: str, value: Any):
        """设置单个配置值"""
        with self._lock:
            config = self.get_config()
            config[key] = value
            self.save_config(config)
    
    # 文件管理方法
    def get_user_upload_dir(self, sid: str) -> str:
        """获取用户上传目录"""
        user_dir = os.path.join(self.data_dir, "uploads", sid)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def get_user_result_dir(self, sid: str) -> str:
        """获取用户结果目录"""
        user_dir = os.path.join(self.data_dir, "results", sid)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def cleanup_expired_data(self, retention_days: int = 7):
        """清理过期数据"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            cutoff_str = cutoff_date.isoformat()
            
            # 清理过期任务
            tasks = self.get_tasks()
            expired_tasks = []
            
            for task_id, task in tasks["tasks"].items():
                created_at = task.get("created_at", "")
                if created_at < cutoff_str:
                    expired_tasks.append(task_id)
            
            # 删除过期任务和相关文件
            for task_id in expired_tasks:
                task = tasks["tasks"][task_id]
                
                # 删除相关文件
                for file_path in [task.get("input_file_path"), task.get("output_file_path")]:
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            logger.warning(f"Failed to remove file {file_path}: {e}")
                
                # 删除任务记录
                del tasks["tasks"][task_id]
            
            if expired_tasks:
                self._save_json(self.tasks_file, tasks)
                logger.info(f"Cleaned up {len(expired_tasks)} expired tasks")
            
            # 清理过期会话
            sessions = self.get_sessions()
            expired_sessions = []
            
            for sid, session in sessions["sessions"].items():
                last_accessed = session.get("last_accessed", "")
                if last_accessed < cutoff_str:
                    expired_sessions.append(sid)
            
            for sid in expired_sessions:
                del sessions["sessions"][sid]
            
            if expired_sessions:
                self._save_json(self.sessions_file, sessions)
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
    
    def get_storage_stats(self) -> Dict:
        """获取存储统计信息"""
        try:
            tasks = self.get_tasks()
            sessions = self.get_sessions()
            
            # 统计任务状态
            task_stats = {}
            for task in tasks["tasks"].values():
                status = task.get("status", "unknown")
                task_stats[status] = task_stats.get(status, 0) + 1
            
            # 计算存储大小
            def get_dir_size(path):
                total = 0
                try:
                    for dirpath, dirnames, filenames in os.walk(path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            if os.path.exists(filepath):
                                total += os.path.getsize(filepath)
                except:
                    pass
                return total
            
            return {
                "total_tasks": len(tasks["tasks"]),
                "total_sessions": len(sessions["sessions"]),
                "task_status_counts": task_stats,
                "upload_dir_size": get_dir_size(os.path.join(self.data_dir, "uploads")),
                "result_dir_size": get_dir_size(os.path.join(self.data_dir, "results")),
                "data_dir": self.data_dir
            }
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}