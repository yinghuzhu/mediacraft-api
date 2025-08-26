"""
用户模型
简化但可扩展的用户数据模型
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

class User:
    """用户模型 - 简化但支持未来扩展"""
    
    def __init__(self, user_id: str = None):
        """初始化用户"""
        self.user_id = user_id or str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.tasks = []  # 任务ID列表
        self.metadata = {}  # 预留扩展空间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'tasks': self.tasks,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """从字典创建用户对象"""
        user = cls(user_id=data['user_id'])
        
        # 解析时间字段
        if data.get('created_at'):
            user.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('last_accessed'):
            user.last_accessed = datetime.fromisoformat(data['last_accessed'])
        
        user.tasks = data.get('tasks', [])
        user.metadata = data.get('metadata', {})
        
        return user
    
    def update_last_accessed(self):
        """更新最后访问时间"""
        self.last_accessed = datetime.utcnow()
    
    def add_task(self, task_id: str):
        """添加任务ID"""
        if task_id not in self.tasks:
            self.tasks.append(task_id)
    
    def remove_task(self, task_id: str):
        """移除任务ID"""
        if task_id in self.tasks:
            self.tasks.remove(task_id)
    
    def get_task_count(self) -> int:
        """获取任务数量"""
        return len(self.tasks)
    
    def set_metadata(self, key: str, value: Any):
        """设置元数据"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default=None):
        """获取元数据"""
        return self.metadata.get(key, default)