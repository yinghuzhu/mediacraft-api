"""
Video merge task model for MediaCraft
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


class VideoMergeTask:
    """Video merge task model for combining multiple videos"""
    
    def __init__(self, task_name: str = "Untitled Merge"):
        """Initialize a new video merge task"""
        self.task_uuid = str(uuid.uuid4())
        self.task_name = task_name
        self.total_videos = 0
        self.total_duration = 0.0  # in seconds
        self.output_resolution = ""  # e.g. "1920x1080"
        self.output_format = "mp4"
        
        # File paths
        self.output_file_path = None
        
        # Task status
        self.status = "created"  # created, uploading, processing, completed, failed
        self.progress_percentage = 0
        self.error_message = None
        
        # Processing parameters
        self.merge_mode = "concat"  # concat, blend
        self.audio_handling = "keep_all"  # keep_all, keep_first, remove
        self.quality_preset = "medium"  # fast, medium, high
        
        # Timestamps
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.expires_at = datetime.now() + timedelta(days=1)  # Default expiration: 1 day
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for storage"""
        return {
            'task_uuid': self.task_uuid,
            'task_name': self.task_name,
            'total_videos': self.total_videos,
            'total_duration': self.total_duration,
            'output_resolution': self.output_resolution,
            'output_format': self.output_format,
            'output_file_path': self.output_file_path,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'error_message': self.error_message,
            'merge_mode': self.merge_mode,
            'audio_handling': self.audio_handling,
            'quality_preset': self.quality_preset,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoMergeTask':
        """Create task from dictionary"""
        task = cls(task_name=data.get('task_name', 'Untitled Merge'))
        
        # Set all attributes from dictionary
        task.task_uuid = data['task_uuid']
        task.total_videos = data.get('total_videos', 0)
        task.total_duration = data.get('total_duration', 0.0)
        task.output_resolution = data.get('output_resolution', '')
        task.output_format = data.get('output_format', 'mp4')
        task.output_file_path = data.get('output_file_path')
        task.status = data.get('status', 'created')
        task.progress_percentage = data.get('progress_percentage', 0)
        task.error_message = data.get('error_message')
        task.merge_mode = data.get('merge_mode', 'concat')
        task.audio_handling = data.get('audio_handling', 'keep_all')
        task.quality_preset = data.get('quality_preset', 'medium')
        
        # Parse datetime fields
        if data.get('created_at'):
            task.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            task.started_at = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            task.completed_at = datetime.fromisoformat(data['completed_at'])
        if data.get('expires_at'):
            task.expires_at = datetime.fromisoformat(data['expires_at'])
        
        return task
    
    def update_status(self, new_status: str) -> bool:
        """Update task status with validation"""
        valid_statuses = ['created', 'uploading', 'processing', 'completed', 'failed']
        
        if new_status not in valid_statuses:
            return False
        
        # Validate status transitions
        if self.status == 'completed' and new_status != 'failed':
            return False  # Can't change from completed except to failed
        
        if self.status == 'failed' and new_status not in ['created', 'processing']:
            return False  # Failed can only go back to created or processing
        
        # Update status and related fields
        self.status = new_status
        
        if new_status == 'processing' and not self.started_at:
            self.started_at = datetime.now()
        
        if new_status == 'completed':
            self.completed_at = datetime.now()
            self.progress_percentage = 100
        
        if new_status == 'failed':
            if not self.error_message:
                self.error_message = "Task failed without specific error message"
        
        return True
    
    def update_progress(self, percentage: int) -> bool:
        """Update progress percentage with validation"""
        if not 0 <= percentage <= 100:
            return False
        
        self.progress_percentage = percentage
        return True
    
    def is_expired(self) -> bool:
        """Check if task has expired"""
        if not self.expires_at:
            return False
        
        return datetime.now() > self.expires_at
    
    def extend_expiration(self, days: int = 1) -> None:
        """Extend expiration date"""
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(days=days)
        else:
            self.expires_at = self.expires_at + timedelta(days=days)
    
    def calculate_total_duration(self, item_durations: List[float]) -> None:
        """Calculate and update total duration based on video items"""
        if not item_durations:
            self.total_duration = 0.0
            return
        
        self.total_duration = sum(item_durations)
        self.total_videos = len(item_durations)