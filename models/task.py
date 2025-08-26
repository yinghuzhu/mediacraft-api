"""
Task model for video watermark removal
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

class VideoWatermarkTask:
    """Video watermark removal task"""
    
    def __init__(self, original_filename: str, file_size: int, video_format: str, original_file_path: str = None):
        """Initialize a new task"""
        self.task_uuid = str(uuid.uuid4())
        self.original_filename = original_filename
        self.file_size = file_size
        self.video_format = video_format
        self.video_duration = None
        self.video_resolution = None
        self.fps = None
        self.original_file_path = original_file_path
        self.processed_file_path = None
        self.status = 'uploaded'
        self.progress_percentage = 0
        self.error_message = None
        self.selected_frame_number = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            'task_uuid': self.task_uuid,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'video_format': self.video_format,
            'video_duration': self.video_duration,
            'video_resolution': self.video_resolution,
            'fps': self.fps,
            'original_file_path': self.original_file_path,
            'processed_file_path': self.processed_file_path,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'error_message': self.error_message,
            'selected_frame_number': self.selected_frame_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoWatermarkTask':
        """Create task from dictionary"""
        task = cls(
            original_filename=data['original_filename'],
            file_size=data['file_size'],
            video_format=data['video_format']
        )
        
        # Set all attributes from dictionary
        task.task_uuid = data['task_uuid']
        task.video_duration = data.get('video_duration')
        task.video_resolution = data.get('video_resolution')
        task.fps = data.get('fps')
        task.original_file_path = data.get('original_file_path')
        task.processed_file_path = data.get('processed_file_path')
        task.status = data.get('status', 'uploaded')
        task.progress_percentage = data.get('progress_percentage', 0)
        task.error_message = data.get('error_message')
        task.selected_frame_number = data.get('selected_frame_number')
        
        # Parse datetime fields
        if data.get('created_at'):
            task.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            task.started_at = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            task.completed_at = datetime.fromisoformat(data['completed_at'])
        
        return task