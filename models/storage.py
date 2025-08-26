"""
Storage model for tasks, regions, and merge operations
"""

import os
import json
import time
import shutil
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from config import get_current_config
from .task import VideoWatermarkTask
from .merge_task import VideoMergeTask
from .merge_video_item import MergeVideoItem

class TaskStorage:
    """Storage for tasks, regions, and merge operations"""
    
    def __init__(self):
        """Initialize storage"""
        # Watermark removal directories
        self.tasks_dir = os.path.join(get_current_config().STORAGE_DIR, 'tasks')
        self.regions_dir = os.path.join(get_current_config().STORAGE_DIR, 'regions')
        self.logs_dir = os.path.join(get_current_config().STORAGE_DIR, 'logs')
        
        # Video merge directories
        self.merge_tasks_dir = os.path.join(get_current_config().STORAGE_DIR, 'merge_tasks')
        self.merge_logs_dir = os.path.join(get_current_config().STORAGE_DIR, 'merge_logs')
        self.merge_temp_dir = os.path.join(get_current_config().TEMP_DIR, 'merge_temp')
        
        # Create directories
        os.makedirs(self.tasks_dir, exist_ok=True)
        os.makedirs(self.regions_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.merge_tasks_dir, exist_ok=True)
        os.makedirs(self.merge_logs_dir, exist_ok=True)
        os.makedirs(self.merge_temp_dir, exist_ok=True)
        
        # In-memory cache
        self.tasks_cache = {}
        self.regions_cache = {}
        self.merge_tasks_cache = {}
        self.merge_items_cache = {}
    
    # ===== Watermark Removal Task Methods =====
    
    def save_task(self, task: VideoWatermarkTask) -> bool:
        """Save task to storage"""
        try:
            # Update cache
            self.tasks_cache[task.task_uuid] = task
            
            # Save to file
            task_path = os.path.join(self.tasks_dir, f"{task.task_uuid}.json")
            with open(task_path, 'w', encoding='utf-8') as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to save task: {e}")
            return False
    
    def get_task(self, task_uuid: str) -> Optional[VideoWatermarkTask]:
        """Get task from storage"""
        try:
            # Check cache first
            if task_uuid in self.tasks_cache:
                return self.tasks_cache[task_uuid]
            
            # Load from file
            task_path = os.path.join(self.tasks_dir, f"{task_uuid}.json")
            if os.path.exists(task_path):
                with open(task_path, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                
                task = VideoWatermarkTask.from_dict(task_data)
                self.tasks_cache[task_uuid] = task
                return task
            
            return None
        except Exception as e:
            print(f"Failed to get task: {e}")
            return None
    
    def save_regions(self, task_uuid: str, regions: List[Dict[str, Any]]) -> bool:
        """Save regions to storage"""
        try:
            # Update cache
            self.regions_cache[task_uuid] = regions
            
            # Save to file
            regions_path = os.path.join(self.regions_dir, f"{task_uuid}.json")
            with open(regions_path, 'w', encoding='utf-8') as f:
                json.dump(regions, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to save regions: {e}")
            return False
    
    def get_regions(self, task_uuid: str) -> List[Dict[str, Any]]:
        """Get regions from storage"""
        try:
            # Check cache first
            if task_uuid in self.regions_cache:
                return self.regions_cache[task_uuid]
            
            # Load from file
            regions_path = os.path.join(self.regions_dir, f"{task_uuid}.json")
            if os.path.exists(regions_path):
                with open(regions_path, 'r', encoding='utf-8') as f:
                    regions = json.load(f)
                
                self.regions_cache[task_uuid] = regions
                return regions
            
            return []
        except Exception as e:
            print(f"Failed to get regions: {e}")
            return []
    
    def add_log(self, task_uuid: str, level: str, message: str, stage: str = None) -> bool:
        """Add log entry"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'stage': stage
            }
            
            # Append to log file
            log_path = os.path.join(self.logs_dir, f"{task_uuid}.log")
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            # Print to console
            print(f"[{level.upper()}] {task_uuid} - {stage or 'GENERAL'}: {message}")
            
            return True
        except Exception as e:
            print(f"Failed to add log: {e}")
            return False
    
    # ===== Video Merge Task Methods =====
    
    def save_merge_task(self, task: VideoMergeTask) -> bool:
        """Save merge task to storage"""
        try:
            # Update cache
            self.merge_tasks_cache[task.task_uuid] = task
            
            # Save to file
            task_path = os.path.join(self.merge_tasks_dir, f"{task.task_uuid}.json")
            with open(task_path, 'w', encoding='utf-8') as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to save merge task: {e}")
            return False
    
    def get_merge_task(self, task_uuid: str) -> Optional[VideoMergeTask]:
        """Get merge task from storage"""
        try:
            # Check cache first
            if task_uuid in self.merge_tasks_cache:
                return self.merge_tasks_cache[task_uuid]
            
            # Load from file
            task_path = os.path.join(self.merge_tasks_dir, f"{task_uuid}.json")
            if os.path.exists(task_path):
                with open(task_path, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                
                task = VideoMergeTask.from_dict(task_data)
                self.merge_tasks_cache[task_uuid] = task
                return task
            
            return None
        except Exception as e:
            print(f"Failed to get merge task: {e}")
            return None
    
    def delete_merge_task(self, task_uuid: str) -> bool:
        """Delete merge task and associated files"""
        try:
            # Get task to access file paths
            task = self.get_merge_task(task_uuid)
            if not task:
                return False
            
            # Delete output file if exists
            if task.output_file_path and os.path.exists(task.output_file_path):
                os.remove(task.output_file_path)
            
            # Delete task file
            task_path = os.path.join(self.merge_tasks_dir, f"{task.task_uuid}.json")
            if os.path.exists(task_path):
                os.remove(task_path)
            
            # Delete items file
            items_path = os.path.join(self.merge_tasks_dir, f"{task.task_uuid}_items.json")
            if os.path.exists(items_path):
                os.remove(items_path)
            
            # Delete log file
            log_path = os.path.join(self.merge_logs_dir, f"{task.task_uuid}.log")
            if os.path.exists(log_path):
                os.remove(log_path)
            
            # Delete temp directory
            temp_dir = os.path.join(self.merge_temp_dir, task.task_uuid)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            # Remove from cache
            if task_uuid in self.merge_tasks_cache:
                del self.merge_tasks_cache[task_uuid]
            if task_uuid in self.merge_items_cache:
                del self.merge_items_cache[task_uuid]
            
            return True
        except Exception as e:
            print(f"Failed to delete merge task: {e}")
            return False
    
    def save_video_items(self, task_uuid: str, items: List[MergeVideoItem]) -> bool:
        """Save video items to storage"""
        try:
            # Update cache
            self.merge_items_cache[task_uuid] = items
            
            # Convert items to dictionaries
            items_data = [item.to_dict() for item in items]
            
            # Save to file
            items_path = os.path.join(self.merge_tasks_dir, f"{task_uuid}_items.json")
            with open(items_path, 'w', encoding='utf-8') as f:
                json.dump(items_data, f, ensure_ascii=False, indent=2)
            
            # Update task total_videos count
            task = self.get_merge_task(task_uuid)
            if task:
                task.total_videos = len(items)
                self.save_merge_task(task)
            
            return True
        except Exception as e:
            print(f"Failed to save video items: {e}")
            return False
    
    def get_video_items(self, task_uuid: str) -> List[MergeVideoItem]:
        """Get video items from storage"""
        try:
            # Check cache first
            if task_uuid in self.merge_items_cache:
                return self.merge_items_cache[task_uuid]
            
            # Load from file
            items_path = os.path.join(self.merge_tasks_dir, f"{task_uuid}_items.json")
            if os.path.exists(items_path):
                with open(items_path, 'r', encoding='utf-8') as f:
                    items_data = json.load(f)
                
                items = [MergeVideoItem.from_dict(item_data) for item_data in items_data]
                self.merge_items_cache[task_uuid] = items
                return items
            
            return []
        except Exception as e:
            print(f"Failed to get video items: {e}")
            return []
    
    def update_video_item(self, task_uuid: str, item: MergeVideoItem) -> bool:
        """Update a specific video item"""
        try:
            items = self.get_video_items(task_uuid)
            if not items:
                return False
            
            # Find and update the item
            updated = False
            for i, existing_item in enumerate(items):
                if existing_item.item_id == item.item_id:
                    items[i] = item
                    updated = True
                    break
            
            if not updated:
                return False
            
            # Save updated items
            return self.save_video_items(task_uuid, items)
        except Exception as e:
            print(f"Failed to update video item: {e}")
            return False
    
    def update_video_order(self, task_uuid: str, new_order: List[str]) -> bool:
        """Update video items order based on item_id list"""
        try:
            items = self.get_video_items(task_uuid)
            if not items:
                return False
            
            # Create a map of item_id to item
            item_map = {item.item_id: item for item in items}
            
            # Create new ordered list
            new_items = []
            for i, item_id in enumerate(new_order):
                if item_id in item_map:
                    item = item_map[item_id]
                    item.item_order = i + 1  # Order starts from 1
                    new_items.append(item)
            
            # Ensure all items are included
            if len(new_items) != len(items):
                return False
            
            # Save updated items
            return self.save_video_items(task_uuid, new_items)
        except Exception as e:
            print(f"Failed to update video order: {e}")
            return False
    
    def add_merge_log(self, task_uuid: str, level: str, message: str, stage: str = None) -> bool:
        """Add merge task log entry"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'stage': stage
            }
            
            # Append to log file
            log_path = os.path.join(self.merge_logs_dir, f"{task_uuid}.log")
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            # Print to console
            print(f"[MERGE][{level.upper()}] {task_uuid} - {stage or 'GENERAL'}: {message}")
            
            return True
        except Exception as e:
            print(f"Failed to add merge log: {e}")
            return False
    
    def get_merge_task_temp_dir(self, task_uuid: str) -> str:
        """Get or create temporary directory for merge task"""
        temp_dir = os.path.join(self.merge_temp_dir, task_uuid)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create subdirectories
        segments_dir = os.path.join(temp_dir, 'segments')
        output_dir = os.path.join(temp_dir, 'output')
        os.makedirs(segments_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        return temp_dir
    
    # ===== Common Methods =====
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old tasks and files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            removed_count = 0
            
            # Clean up watermark removal tasks
            removed_count += self._cleanup_watermark_tasks(cutoff_date)
            
            # Clean up merge tasks
            removed_count += self._cleanup_merge_tasks(cutoff_date)
            
            return removed_count
        except Exception as e:
            print(f"Failed to clean up old tasks: {e}")
            return 0
    
    def _cleanup_watermark_tasks(self, cutoff_date: datetime) -> int:
        """Clean up old watermark removal tasks"""
        removed_count = 0
        
        # Iterate through task files
        for filename in os.listdir(self.tasks_dir):
            if not filename.endswith('.json'):
                continue
            
            task_path = os.path.join(self.tasks_dir, filename)
            try:
                # Check file modification time
                if datetime.fromtimestamp(os.path.getmtime(task_path)) < cutoff_date:
                    # Load task to get file paths
                    with open(task_path, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                    
                    # Remove original file
                    original_path = task_data.get('original_file_path')
                    if original_path and os.path.exists(original_path):
                        os.remove(original_path)
                    
                    # Remove processed file
                    processed_path = task_data.get('processed_file_path')
                    if processed_path and os.path.exists(processed_path):
                        os.remove(processed_path)
                    
                    # Remove regions file
                    task_uuid = task_data.get('task_uuid')
                    regions_path = os.path.join(self.regions_dir, f"{task_uuid}.json")
                    if os.path.exists(regions_path):
                        os.remove(regions_path)
                    
                    # Remove log file
                    log_path = os.path.join(self.logs_dir, f"{task_uuid}.log")
                    if os.path.exists(log_path):
                        os.remove(log_path)
                    
                    # Remove task file
                    os.remove(task_path)
                    
                    # Remove from cache
                    if task_uuid in self.tasks_cache:
                        del self.tasks_cache[task_uuid]
                    if task_uuid in self.regions_cache:
                        del self.regions_cache[task_uuid]
                    
                    removed_count += 1
            except Exception as e:
                print(f"Error cleaning up watermark task {filename}: {e}")
        
        return removed_count
    
    def _cleanup_merge_tasks(self, cutoff_date: datetime) -> int:
        """Clean up old merge tasks"""
        removed_count = 0
        
        # Iterate through merge task files
        for filename in os.listdir(self.merge_tasks_dir):
            if not filename.endswith('.json') or '_items' in filename:
                continue
            
            task_path = os.path.join(self.merge_tasks_dir, filename)
            try:
                # Check file modification time
                if datetime.fromtimestamp(os.path.getmtime(task_path)) < cutoff_date:
                    # Load task to get UUID
                    with open(task_path, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                    
                    task_uuid = task_data.get('task_uuid')
                    if task_uuid:
                        # Use delete_merge_task to clean up all related files
                        if self.delete_merge_task(task_uuid):
                            removed_count += 1
            except Exception as e:
                print(f"Error cleaning up merge task {filename}: {e}")
        
        return removed_count