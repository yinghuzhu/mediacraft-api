"""
用户管理器
基于会话ID的用户数据管理
"""
import os
import sys
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

# 确保可以导入 models 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User

logger = logging.getLogger(__name__)

class UserManager:
    """用户管理器 - 管理用户数据和会话关联"""
    
    def __init__(self, storage_manager):
        self.storage = storage_manager
        self.users_file = "users.json"
    
    def _load_users(self) -> Dict:
        """加载用户数据"""
        users_file_path = os.path.join(self.storage.data_dir, self.users_file)
        return self.storage._load_json(users_file_path, {"users": {}})
    
    def _save_users(self, users_data: Dict):
        """保存用户数据"""
        users_file_path = os.path.join(self.storage.data_dir, self.users_file)
        self.storage._save_json(users_file_path, users_data)
    
    def get_or_create_user(self, user_id: str) -> User:
        """获取或创建用户"""
        try:
            users_data = self._load_users()
            
            if user_id in users_data["users"]:
                # 用户存在，更新最后访问时间
                user = User.from_dict(users_data["users"][user_id])
                user.update_last_accessed()
                
                # 保存更新
                users_data["users"][user_id] = user.to_dict()
                self._save_users(users_data)
                
                return user
            else:
                # 创建新用户
                user = User(user_id=user_id)
                users_data["users"][user_id] = user.to_dict()
                self._save_users(users_data)
                
                logger.info(f"Created new user: {user_id}")
                return user
                
        except Exception as e:
            logger.error(f"Failed to get or create user {user_id}: {e}")
            # 返回临时用户对象
            return User(user_id=user_id)
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        try:
            users_data = self._load_users()
            
            if user_id in users_data["users"]:
                return User.from_dict(users_data["users"][user_id])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def save_user(self, user: User):
        """保存用户数据"""
        try:
            users_data = self._load_users()
            users_data["users"][user.user_id] = user.to_dict()
            self._save_users(users_data)
            
        except Exception as e:
            logger.error(f"Failed to save user {user.user_id}: {e}")
            raise
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        try:
            users_data = self._load_users()
            
            if user_id in users_data["users"]:
                del users_data["users"][user_id]
                self._save_users(users_data)
                logger.info(f"Deleted user: {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    def get_user_info(self, user_id: str) -> Dict:
        """获取用户信息和统计"""
        try:
            user = self.get_user(user_id)
            if not user:
                return {}
            
            # 获取用户任务统计
            user_tasks = self.storage.get_user_tasks(user_id)
            
            task_stats = {}
            for task in user_tasks:
                status = task.get('status', 'unknown')
                task_stats[status] = task_stats.get(status, 0) + 1
            
            return {
                'user_id': user.user_id,
                'created_at': user.created_at.isoformat(),
                'last_accessed': user.last_accessed.isoformat(),
                'task_count': user.get_task_count(),
                'task_stats': task_stats,
                'metadata': user.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {e}")
            return {}
    
    def get_user_tasks(self, user_id: str) -> List[Dict]:
        """获取用户的所有任务"""
        try:
            return self.storage.get_user_tasks(user_id)
        except Exception as e:
            logger.error(f"Failed to get user tasks for {user_id}: {e}")
            return []
    
    def add_task_to_user(self, user_id: str, task_id: str):
        """为用户添加任务"""
        try:
            user = self.get_or_create_user(user_id)
            user.add_task(task_id)
            self.save_user(user)
            
        except Exception as e:
            logger.error(f"Failed to add task {task_id} to user {user_id}: {e}")
            raise
    
    def remove_task_from_user(self, user_id: str, task_id: str):
        """从用户中移除任务"""
        try:
            user = self.get_user(user_id)
            if user:
                user.remove_task(task_id)
                self.save_user(user)
                
        except Exception as e:
            logger.error(f"Failed to remove task {task_id} from user {user_id}: {e}")
    
    def cleanup_inactive_users(self, inactive_days: int = 30):
        """清理不活跃用户"""
        try:
            users_data = self._load_users()
            cutoff_date = datetime.utcnow() - timedelta(days=inactive_days)
            inactive_users = []
            
            for user_id, user_data in users_data["users"].items():
                last_accessed_str = user_data.get("last_accessed", "")
                if last_accessed_str:
                    try:
                        last_accessed = datetime.fromisoformat(last_accessed_str)
                        if last_accessed < cutoff_date:
                            inactive_users.append(user_id)
                    except ValueError:
                        # 无效的时间格式，标记为不活跃
                        inactive_users.append(user_id)
            
            # 删除不活跃用户
            for user_id in inactive_users:
                del users_data["users"][user_id]
            
            if inactive_users:
                self._save_users(users_data)
                logger.info(f"Cleaned up {len(inactive_users)} inactive users")
            
        except Exception as e:
            logger.error(f"Failed to cleanup inactive users: {e}")
    
    def get_user_stats(self) -> Dict:
        """获取用户统计信息"""
        try:
            users_data = self._load_users()
            total_users = len(users_data["users"])
            
            # 统计活跃用户（最近7天有访问）
            active_cutoff = datetime.utcnow() - timedelta(days=7)
            active_users = 0
            
            for user_data in users_data["users"].values():
                last_accessed_str = user_data.get("last_accessed", "")
                if last_accessed_str:
                    try:
                        last_accessed = datetime.fromisoformat(last_accessed_str)
                        if last_accessed > active_cutoff:
                            active_users += 1
                    except ValueError:
                        pass
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users
            }
            
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "inactive_users": 0
            }