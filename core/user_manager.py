"""
用户管理器
基于会话ID的用户数据管理
"""
import os
import sys
import logging
import hashlib
import secrets
from typing import Optional, Dict, List
from datetime import datetime, timedelta

# 确保可以导入 models 模块 - 使用相对于backend-repo根目录的路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User

logger = logging.getLogger(__name__)

class UserManager:
    """用户管理器 - 管理用户数据和会话关联"""
    
    def __init__(self, storage_manager):
        self.storage = storage_manager
        self.users_file = "users.json"
        self.auth_users_file = "auth_users.json"  # 存储认证用户信息
        self.user_sessions_file = "user_sessions.json"  # 存储用户会话关联
    
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
    
    def _load_auth_users(self) -> Dict:
        """加载认证用户数据"""
        auth_file_path = os.path.join(self.storage.data_dir, self.auth_users_file)
        return self.storage._load_json(auth_file_path, {"auth_users": {}})
    
    def _save_auth_users(self, auth_data: Dict):
        """保存认证用户数据"""
        auth_file_path = os.path.join(self.storage.data_dir, self.auth_users_file)
        self.storage._save_json(auth_file_path, auth_data)
    
    def _load_user_sessions(self) -> Dict:
        """加载用户会话关联数据"""
        sessions_file_path = os.path.join(self.storage.data_dir, self.user_sessions_file)
        return self.storage._load_json(sessions_file_path, {"user_sessions": {}, "session_users": {}})
    
    def _save_user_sessions(self, sessions_data: Dict):
        """保存用户会话关联数据"""
        sessions_file_path = os.path.join(self.storage.data_dir, self.user_sessions_file)
        self.storage._save_json(sessions_file_path, sessions_data)
    
    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """哈希密码"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用 PBKDF2 进行密码哈希
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                          password.encode('utf-8'), 
                                          salt.encode('utf-8'), 
                                          100000)  # 100,000 iterations
        return password_hash.hex(), salt
    
    def register_user(self, username: str, password: str, email: str = None) -> Dict:
        """注册新用户"""
        try:
            auth_data = self._load_auth_users()
            
            # 检查用户名是否已存在
            if username in auth_data["auth_users"]:
                return {
                    "success": False,
                    "message": "用户名已存在"
                }
            
            # 检查邮箱是否已存在
            if email:
                for user_info in auth_data["auth_users"].values():
                    if user_info.get("email") == email:
                        return {
                            "success": False,
                            "message": "邮箱已被使用"
                        }
            
            # 哈希密码
            password_hash, salt = self._hash_password(password)
            
            # 生成用户ID
            user_id = f"user_{secrets.token_hex(8)}"
            
            # 保存认证信息
            auth_data["auth_users"][username] = {
                "user_id": user_id,
                "username": username,
                "password_hash": password_hash,
                "salt": salt,
                "email": email,
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True
            }
            
            self._save_auth_users(auth_data)
            
            # 创建用户数据记录
            self.get_or_create_user(user_id)
            
            logger.info(f"User registered successfully: {username} (ID: {user_id})")
            
            return {
                "success": True,
                "message": "用户注册成功",
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Failed to register user {username}: {e}")
            return {
                "success": False,
                "message": "注册失败，请稍后重试"
            }
    
    def authenticate_user(self, username: str, password: str) -> Dict:
        """验证用户登录"""
        try:
            auth_data = self._load_auth_users()
            
            # 检查用户是否存在
            if username not in auth_data["auth_users"]:
                return {
                    "success": False,
                    "message": "用户名或密码错误"
                }
            
            user_info = auth_data["auth_users"][username]
            
            # 检查用户是否激活
            if not user_info.get("is_active", True):
                return {
                    "success": False,
                    "message": "账户已被禁用"
                }
            
            # 验证密码
            stored_hash = user_info["password_hash"]
            salt = user_info["salt"]
            password_hash, _ = self._hash_password(password, salt)
            
            if password_hash != stored_hash:
                return {
                    "success": False,
                    "message": "用户名或密码错误"
                }
            
            # 更新最后登录时间
            user_info["last_login"] = datetime.utcnow().isoformat()
            auth_data["auth_users"][username] = user_info
            self._save_auth_users(auth_data)
            
            # 返回用户信息（不包含敏感信息）
            safe_user_info = {
                "user_id": user_info["user_id"],
                "username": user_info["username"],
                "email": user_info.get("email"),
                "created_at": user_info["created_at"],
                "last_login": user_info.get("last_login")
            }
            
            return {
                "success": True,
                "message": "登录成功",
                "user": safe_user_info
            }
            
        except Exception as e:
            logger.error(f"Failed to authenticate user {username}: {e}")
            return {
                "success": False,
                "message": "登录失败，请稍后重试"
            }
    
    def associate_user_session(self, user_id: str, session_id: str):
        """关联用户和会话"""
        try:
            sessions_data = self._load_user_sessions()
            
            # 双向关联
            sessions_data["user_sessions"][user_id] = session_id
            sessions_data["session_users"][session_id] = user_id
            
            self._save_user_sessions(sessions_data)
            
            logger.info(f"Associated user {user_id} with session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to associate user {user_id} with session {session_id}: {e}")
            raise
    
    def disassociate_user_session(self, session_id: str):
        """解除用户会话关联"""
        try:
            sessions_data = self._load_user_sessions()
            
            # 获取用户ID
            user_id = sessions_data["session_users"].get(session_id)
            
            if user_id:
                # 移除双向关联
                sessions_data["user_sessions"].pop(user_id, None)
                sessions_data["session_users"].pop(session_id, None)
                
                self._save_user_sessions(sessions_data)
                
                logger.info(f"Disassociated user {user_id} from session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to disassociate session {session_id}: {e}")
    
    def get_user_by_session(self, session_id: str) -> Optional[str]:
        """通过会话ID获取用户ID"""
        try:
            sessions_data = self._load_user_sessions()
            return sessions_data["session_users"].get(session_id)
            
        except Exception as e:
            logger.error(f"Failed to get user by session {session_id}: {e}")
            return None
    
    def get_session_by_user(self, user_id: str) -> Optional[str]:
        """通过用户ID获取会话ID"""
        try:
            sessions_data = self._load_user_sessions()
            return sessions_data["user_sessions"].get(user_id)
            
        except Exception as e:
            logger.error(f"Failed to get session by user {user_id}: {e}")
            return None