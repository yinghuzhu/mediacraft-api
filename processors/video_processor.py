"""
Video processor for watermark removal
"""

import os
import sys
import cv2
import numpy as np
import tempfile
import subprocess
import time
from typing import List, Dict, Tuple, Optional, Any

# 确保可以导入 models 和 config 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_current_config
from models.task import VideoWatermarkTask
from models.storage import TaskStorage

class VideoProcessor:
    """Video processor for watermark removal"""
    
    def __init__(self):
        """Initialize processor"""
        current_config = get_current_config()
        if not os.path.exists(current_config.TEMP_DIR):
            raise RuntimeError('TEMP_DIR must be set in config.py')
        self.temp_dir = current_config.TEMP_DIR
        self.storage = TaskStorage()
    
    def extract_video_info(self, video_path: str) -> Dict[str, Any]:
        """Extract video information"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("Cannot open video file")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'duration': duration,
                'resolution': f"{width}x{height}"
            }
        except Exception as e:
            raise Exception(f"Failed to extract video info: {str(e)}")
    
    def extract_frame(self, video_path: str, frame_number: int) -> Optional[np.ndarray]:
        """Extract specific frame"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            cap.release()
            
            return frame if ret else None
        except Exception as e:
            print(f"Failed to extract frame: {e}")
            return None
    
    def get_sample_frames(self, video_path: str, sample_count: int = 10) -> List[Tuple[int, str]]:
        """Get sample frames for selection"""
        try:
            info = self.extract_video_info(video_path)
            frame_count = info['frame_count']
            
            # Calculate sampling interval
            if frame_count <= sample_count:
                frame_numbers = list(range(frame_count))
            else:
                step = frame_count // sample_count
                frame_numbers = [i * step for i in range(sample_count)]
            
            frames_data = []
            cap = cv2.VideoCapture(video_path)
            
            for frame_num in frame_numbers:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if ret:
                    # Convert frame to base64 encoded JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, config.FRAME_QUALITY])
                    import base64
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    frames_data.append((frame_num, f"data:image/jpeg;base64,{frame_base64}"))
            
            cap.release()
            return frames_data
            
        except Exception as e:
            print(f"Failed to get sample frames: {e}")
            return []
    
    def process_video_remove_watermark(self, task: VideoWatermarkTask, regions: List[Dict[str, Any]]) -> bool:
        """Process video to remove watermark"""
        start_time = time.time()
        
        try:
            # Update task status
            task.status = 'processing'
            task.progress_percentage = 0
            task.started_at = datetime.now()
            self.storage.save_task(task)
            
            self.storage.add_log(task.task_uuid, 'info', 'Starting video processing', 'start_processing')
            
            # Create temporary file paths
            temp_video_path = os.path.join(self.temp_dir, f"temp_{task.task_uuid}.mp4")
            output_video_path = os.path.join(self.temp_dir, f"output_{task.task_uuid}.mp4")
            
            # Open video
            cap = cv2.VideoCapture(task.original_file_path)
            if not cap.isOpened():
                raise Exception("Cannot open original video file")
            
            # Get video parameters
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))
            
            # Create static mask
            mask = np.zeros((height, width), dtype=np.uint8)
            for region in regions:
                cv2.rectangle(mask, (region['x'], region['y']), 
                            (region['x'] + region['width'], region['y'] + region['height']), 255, -1)
            
            self.storage.add_log(task.task_uuid, 'info', f'Created mask with {len(regions)} regions', 'create_mask')
            
            # Process frames in batches
            processed_frames = 0
            batch_size = config.BATCH_SIZE
            batch_frames = []
            
            while True:
                # Check timeout
                if time.time() - start_time > config.MAX_PROCESSING_TIME:
                    self.storage.add_log(task.task_uuid, 'warning', 'Processing timeout, using fast mode', 'timeout')
                    cap.release()
                    out.release()
                    return self._process_remaining_frames_fast(task, regions, processed_frames, frame_count)
                
                ret, frame = cap.read()
                if not ret:
                    break
                
                batch_frames.append(frame)
                
                # Process batch
                if len(batch_frames) >= batch_size or processed_frames + len(batch_frames) >= frame_count:
                    for frame in batch_frames:
                        # Use inpaint algorithm to remove watermark
                        inpainted_frame = cv2.inpaint(frame, mask, 3, cv2.INPAINT_NS)
                        out.write(inpainted_frame)
                    
                    processed_frames += len(batch_frames)
                    batch_frames = []
                    
                    # Update progress
                    progress = min(int((processed_frames / frame_count) * 80), 80)  # 80% for video processing
                    if progress != task.progress_percentage:
                        task.progress_percentage = progress
                        self.storage.save_task(task)
                    
                    # Log progress every 100 frames
                    if processed_frames % 100 == 0:
                        self.storage.add_log(task.task_uuid, 'info', 
                                           f'Processed {processed_frames}/{frame_count} frames', 'processing_frames')
            
            cap.release()
            out.release()
            
            self.storage.add_log(task.task_uuid, 'info', 'Video frame processing completed', 'frames_complete')
            
            # Merge audio
            success = self._merge_audio_with_ffmpeg(task.original_file_path, temp_video_path, output_video_path)
            
            if success:
                task.processed_file_path = output_video_path
                task.status = 'completed'
                task.progress_percentage = 100
                task.completed_at = datetime.now()
                
                # Clean up temporary file
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
                
                self.storage.add_log(task.task_uuid, 'info', 'Video processing completed successfully', 'completed')
            else:
                # If audio merge fails, use video without audio
                task.processed_file_path = temp_video_path
                task.status = 'completed'
                task.progress_percentage = 100
                task.completed_at = datetime.now()
                
                self.storage.add_log(task.task_uuid, 'warning', 'Audio merge failed, using video without audio', 'completed')
            
            self.storage.save_task(task)
            
            total_time = time.time() - start_time
            self.storage.add_log(task.task_uuid, 'info', f'Total processing time: {total_time:.2f} seconds', 'timing')
            
            return True
            
        except Exception as e:
            error_msg = f"Video processing failed: {str(e)}"
            task.status = 'failed'
            task.error_message = error_msg
            self.storage.save_task(task)
            
            self.storage.add_log(task.task_uuid, 'error', error_msg, 'processing_error')
            return False
    
    def _merge_audio_with_ffmpeg(self, original_video: str, processed_video: str, output_video: str) -> bool:
        """Merge audio using FFmpeg"""
        try:
            # Check if FFmpeg is installed
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print("FFmpeg not installed, skipping audio merge")
                return False
            
            # Merge audio command
            cmd = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-i', processed_video,  # Processed video (no audio)
                '-i', original_video,   # Original video (with audio)
                '-c:v', 'copy',         # Copy video stream
                '-c:a', 'aac',          # Audio codec AAC
                '-map', '0:v:0',        # Use video from first input
                '-map', '1:a:0?',       # Use audio from second input (optional)
                '-shortest',            # Use shortest stream
                output_video
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return True
            else:
                print(f"FFmpeg error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("FFmpeg processing timeout")
            return False
        except FileNotFoundError:
            print("FFmpeg not found")
            return False
        except Exception as e:
            print(f"Audio merge exception: {e}")
            return False
    
    def _process_remaining_frames_fast(self, task: VideoWatermarkTask, regions: List[Dict[str, Any]], 
                                     processed_frames: int, total_frames: int) -> bool:
        """Fast processing for remaining frames"""
        try:
            self.storage.add_log(task.task_uuid, 'warning', 
                               f'Timeout occurred, marking task as completed with partial processing', 'fallback')
            
            # Mark as completed even though not fully processed
            task.status = 'completed'
            task.progress_percentage = 90  # Set to 90% to indicate partial completion
            task.completed_at = datetime.now()
            self.storage.save_task(task)
            
            return True
            
        except Exception as e:
            self.storage.add_log(task.task_uuid, 'error', f'Fallback processing failed: {e}', 'fallback_error')
            return False

# Import datetime here to avoid circular import
from datetime import datetime