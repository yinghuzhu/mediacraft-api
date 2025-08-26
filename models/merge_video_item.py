"""
Merge video item model for MediaCraft
"""

import uuid
import os
from datetime import datetime
from typing import Optional, Dict, Any


class MergeVideoItem:
    """Video item model for merge tasks"""
    
    def __init__(self, original_filename: str, file_size: int, file_path: str, item_order: int = 0):
        """Initialize a new merge video item"""
        self.item_id = str(uuid.uuid4())
        self.item_order = item_order
        
        # Video file information
        self.original_filename = original_filename
        self.file_size = file_size
        self.file_path = file_path
        
        # Video properties
        self.video_duration = 0.0  # in seconds
        self.video_resolution = ""  # e.g. "1920x1080"
        self.video_format = self._extract_format(original_filename)
        self.fps = 0.0
        self.bitrate = 0
        self.has_audio = True
        
        # Time segment settings
        self.start_time = 0.0  # in seconds
        self.end_time = None  # None means until the end
        self.segment_duration = 0.0  # Will be calculated
        
        # Status
        self.status = "uploaded"  # uploaded, analyzed, ready, processing, completed, failed
        
        # Timestamps
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def _extract_format(self, filename: str) -> str:
        """Extract video format from filename"""
        if not filename or '.' not in filename:
            return ""
        
        return filename.rsplit('.', 1)[1].lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert item to dictionary for storage"""
        return {
            'item_id': self.item_id,
            'item_order': self.item_order,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_path': self.file_path,
            'video_duration': self.video_duration,
            'video_resolution': self.video_resolution,
            'video_format': self.video_format,
            'fps': self.fps,
            'bitrate': self.bitrate,
            'has_audio': self.has_audio,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'segment_duration': self.segment_duration,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MergeVideoItem':
        """Create item from dictionary"""
        item = cls(
            original_filename=data['original_filename'],
            file_size=data['file_size'],
            file_path=data['file_path'],
            item_order=data.get('item_order', 0)
        )
        
        # Set all attributes from dictionary
        item.item_id = data['item_id']
        item.video_duration = data.get('video_duration', 0.0)
        item.video_resolution = data.get('video_resolution', '')
        item.video_format = data.get('video_format', '')
        item.fps = data.get('fps', 0.0)
        item.bitrate = data.get('bitrate', 0)
        item.has_audio = data.get('has_audio', True)
        item.start_time = data.get('start_time', 0.0)
        item.end_time = data.get('end_time')
        item.segment_duration = data.get('segment_duration', 0.0)
        item.status = data.get('status', 'uploaded')
        
        # Parse datetime fields
        if data.get('created_at'):
            item.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            item.updated_at = datetime.fromisoformat(data['updated_at'])
        
        return item
    
    def update_video_info(self, duration: float, resolution: str, fps: float, bitrate: int, has_audio: bool) -> None:
        """Update video information after analysis"""
        self.video_duration = duration
        self.video_resolution = resolution
        self.fps = fps
        self.bitrate = bitrate
        self.has_audio = has_audio
        
        # If end_time is not set, use full duration
        if self.end_time is None:
            self.end_time = duration
        
        # Calculate segment duration
        self.calculate_segment_duration()
        
        # Update status
        self.status = "analyzed"
        self.updated_at = datetime.now()
    
    def set_time_segment(self, start_time: float, end_time: Optional[float] = None) -> bool:
        """Set time segment with validation"""
        # Validate start time
        if start_time < 0:
            return False
        
        # If video duration is known, validate against it
        if self.video_duration > 0:
            if start_time >= self.video_duration:
                return False
            
            # If end_time is provided, validate it
            if end_time is not None:
                if end_time <= start_time or end_time > self.video_duration:
                    return False
        elif end_time is not None and end_time <= start_time:
            # If video duration is unknown but end_time is provided
            return False
        
        # Update time segment
        self.start_time = start_time
        self.end_time = end_time
        
        # Calculate segment duration
        self.calculate_segment_duration()
        
        # Update status and timestamp
        self.status = "ready"
        self.updated_at = datetime.now()
        
        return True
    
    def calculate_segment_duration(self) -> None:
        """Calculate segment duration based on start and end times"""
        if self.end_time is None:
            if self.video_duration > 0:
                self.segment_duration = self.video_duration - self.start_time
            else:
                self.segment_duration = 0.0
        else:
            self.segment_duration = self.end_time - self.start_time
        
        # Ensure non-negative duration
        self.segment_duration = max(0.0, self.segment_duration)
    
    def update_status(self, new_status: str) -> bool:
        """Update item status with validation"""
        valid_statuses = ['uploaded', 'analyzed', 'ready', 'processing', 'completed', 'failed']
        
        if new_status not in valid_statuses:
            return False
        
        self.status = new_status
        self.updated_at = datetime.now()
        return True
    
    def file_exists(self) -> bool:
        """Check if the video file exists"""
        return os.path.exists(self.file_path) if self.file_path else False
    
    def get_filename_without_extension(self) -> str:
        """Get filename without extension"""
        if not self.original_filename:
            return ""
        
        return os.path.splitext(self.original_filename)[0]
    
    def get_segment_info(self) -> Dict[str, Any]:
        """Get segment information for processing"""
        return {
            'item_id': self.item_id,
            'file_path': self.file_path,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.segment_duration,
            'has_audio': self.has_audio
        }