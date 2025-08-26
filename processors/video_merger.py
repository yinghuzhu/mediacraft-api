"""
Video merger processor for MediaCraft
"""

import os
import sys
import subprocess
import tempfile
import time
import json
from typing import List, Dict, Tuple, Optional, Any
import cv2

# 确保可以导入 models 和 config 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from models.merge_task import VideoMergeTask
from models.merge_video_item import MergeVideoItem
from models.storage import TaskStorage


class VideoMerger:
    """Video merger processor for combining multiple videos"""
    
    def __init__(self):
        """Initialize processor"""
        self.temp_dir = config.TEMP_DIR
        self.storage = TaskStorage()
    
    def extract_video_info(self, video_path: str) -> Dict[str, Any]:
        """Extract video information using OpenCV"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("Cannot open video file")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Check if video has audio
            has_audio = self._check_audio_stream(video_path)
            
            # Get bitrate using FFmpeg
            bitrate = self._get_video_bitrate(video_path)
            
            cap.release()
            
            return {
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'duration': duration,
                'resolution': f"{width}x{height}",
                'has_audio': has_audio,
                'bitrate': bitrate
            }
        except Exception as e:
            raise Exception(f"Failed to extract video info: {str(e)}")
    
    def _check_audio_stream(self, video_path: str) -> bool:
        """Check if video has audio stream using FFmpeg"""
        try:
            cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-select_streams', 'a:0', 
                '-show_entries', 'stream=codec_type', 
                '-of', 'json', 
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return False
            
            data = json.loads(result.stdout)
            return 'streams' in data and len(data['streams']) > 0
        except Exception:
            return False
    
    def _get_video_bitrate(self, video_path: str) -> int:
        """Get video bitrate using FFmpeg"""
        try:
            cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-select_streams', 'v:0', 
                '-show_entries', 'stream=bit_rate', 
                '-of', 'json', 
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return 0
            
            data = json.loads(result.stdout)
            
            if 'streams' in data and len(data['streams']) > 0:
                bitrate = data['streams'][0].get('bit_rate')
                if bitrate:
                    return int(bitrate)
            
            # If bitrate not found in stream info, calculate from file size and duration
            file_size = os.path.getsize(video_path)
            info = self.extract_video_info(video_path)
            duration = info.get('duration', 0)
            
            if duration > 0:
                # Calculate bitrate in bits per second
                return int((file_size * 8) / duration)
            
            return 0
        except Exception:
            return 0
    
    def analyze_video_item(self, item: MergeVideoItem) -> bool:
        """Analyze video item and update its information"""
        try:
            if not os.path.exists(item.file_path):
                return False
            
            # Extract video information
            info = self.extract_video_info(item.file_path)
            
            # Update item with extracted information
            item.update_video_info(
                duration=info['duration'],
                resolution=info['resolution'],
                fps=info['fps'],
                bitrate=info['bitrate'],
                has_audio=info['has_audio']
            )
            
            return True
        except Exception as e:
            print(f"Failed to analyze video item: {e}")
            return False
    
    def check_format_compatibility(self, items: List[MergeVideoItem]) -> Tuple[bool, str]:
        """Check if all videos have compatible formats for direct merging"""
        if not items:
            return False, "No video items provided"
        
        # Get reference values from first item
        ref_resolution = items[0].video_resolution
        ref_fps = items[0].fps
        
        # Check if all items have similar properties
        for item in items:
            # Resolution mismatch
            if item.video_resolution != ref_resolution:
                return False, f"Resolution mismatch: {item.video_resolution} vs {ref_resolution}"
            
            # FPS difference > 1
            if abs(item.fps - ref_fps) > 1:
                return False, f"FPS mismatch: {item.fps} vs {ref_fps}"
        
        return True, "All videos are compatible"
    
    def get_optimal_output_format(self, items: List[MergeVideoItem]) -> Dict[str, Any]:
        """Determine optimal output format based on input videos"""
        if not items:
            return {
                'resolution': '1280x720',
                'fps': 30,
                'format': 'mp4',
                'codec': 'libx264',
                'audio_codec': 'aac',
                'bitrate': 2000000  # 2 Mbps
            }
        
        # Get highest resolution
        max_width = 0
        max_height = 0
        for item in items:
            if not item.video_resolution:
                continue
                
            try:
                width, height = map(int, item.video_resolution.split('x'))
                max_width = max(max_width, width)
                max_height = max(max_height, height)
            except ValueError:
                continue
        
        # If no valid resolution found, use default
        if max_width == 0 or max_height == 0:
            max_width = 1280
            max_height = 720
        
        # Get highest FPS (but cap at 60)
        max_fps = 30  # Default
        for item in items:
            if item.fps > 0:
                max_fps = max(max_fps, min(item.fps, 60))
        
        # Get highest bitrate (but ensure it's reasonable)
        max_bitrate = 2000000  # Default: 2 Mbps
        for item in items:
            if item.bitrate > 0:
                max_bitrate = max(max_bitrate, item.bitrate)
        
        # Cap bitrate based on resolution
        if max_width >= 3840:  # 4K
            max_bitrate = min(max_bitrate, 20000000)  # 20 Mbps
        elif max_width >= 1920:  # 1080p
            max_bitrate = min(max_bitrate, 8000000)  # 8 Mbps
        elif max_width >= 1280:  # 720p
            max_bitrate = min(max_bitrate, 5000000)  # 5 Mbps
        else:
            max_bitrate = min(max_bitrate, 2500000)  # 2.5 Mbps
        
        return {
            'resolution': f"{max_width}x{max_height}",
            'fps': max_fps,
            'format': 'mp4',
            'codec': 'libx264',
            'audio_codec': 'aac',
            'bitrate': max_bitrate
        }
    
    def process_merge_task(self, task: VideoMergeTask) -> bool:
        start_time = time.time()
        
        try:
            print(f"[MERGE] Task {task.task_uuid} - 开始视频合并处理: {task.task_name}")
            # Update task status
            task.update_status('processing')
            task.progress_percentage = 0
            self.storage.save_merge_task(task)
            
            self.storage.add_merge_log(task.task_uuid, 'info', 'Starting video merge processing', 'start_processing')
            
            # Get video items
            items = self.storage.get_video_items(task.task_uuid)
            if not items:
                print(f"[MERGE] Task {task.task_uuid} - 未找到需要合并的视频项")
                raise Exception("No video items found for merging")
            
            # Sort items by order
            items.sort(key=lambda x: x.item_order)
            
            # Analyze videos if needed
            for i, item in enumerate(items):
                if item.status == 'uploaded':
                    print(f"[MERGE] Task {task.task_uuid} - 分析第{i+1}个视频: {item.original_filename}")
                    self.storage.add_merge_log(task.task_uuid, 'info', f'Analyzing video {i+1}/{len(items)}', 'analyzing')
                    if self.analyze_video_item(item):
                        print(f"[MERGE] Task {task.task_uuid} - 视频分析成功: {item.original_filename}, 时长: {item.video_duration}, 分辨率: {item.video_resolution}, FPS: {item.fps}")
                        self.storage.update_video_item(task.task_uuid, item)
                    else:
                        print(f"[MERGE] Task {task.task_uuid} - 视频分析失败: {item.original_filename}")
                        raise Exception(f"Failed to analyze video: {item.original_filename}")
            
            # Update task progress
            task.progress_percentage = 10
            self.storage.save_merge_task(task)
            
            # Check format compatibility
            compatible, message = self.check_format_compatibility(items)
            if not compatible:
                print(f"[MERGE] Task {task.task_uuid} - 视频格式不兼容: {message}")
                self.storage.add_merge_log(task.task_uuid, 'warning', 
                                         f'Videos are not directly compatible: {message}. Will convert to standard format.', 
                                         'compatibility_check')
            else:
                print(f"[MERGE] Task {task.task_uuid} - 所有视频格式兼容，可以直接合并")
            
            # Get optimal output format
            output_format = self.get_optimal_output_format(items)
            task.output_resolution = output_format['resolution']
            self.storage.save_merge_task(task)
            print(f"[MERGE] Task {task.task_uuid} - 输出分辨率: {output_format['resolution']}, FPS: {output_format['fps']}, 比特率: {output_format['bitrate']}")
            
            # Create temporary directory for this task
            temp_dir = self.storage.get_merge_task_temp_dir(task.task_uuid)
            segments_dir = os.path.join(temp_dir, 'segments')
            output_dir = os.path.join(temp_dir, 'output')
            
            # Process video segments
            self.storage.add_merge_log(task.task_uuid, 'info', 'Processing video segments', 'segmenting')
            segment_files = []
            
            for i, item in enumerate(items):
                # Update progress
                progress = 10 + int((i / len(items)) * 40)  # 10-50% for segmenting
                task.progress_percentage = progress
                self.storage.save_merge_task(task)
                
                print(f"[MERGE] Task {task.task_uuid} - 处理分段: {item.original_filename}, 起止: {item.start_time}-{item.end_time}")
                # Process segment
                segment_path = self._process_video_segment(
                    item, 
                    segments_dir, 
                    i, 
                    output_format
                )
                
                if segment_path:
                    print(f"[MERGE] Task {task.task_uuid} - 分段处理成功: {segment_path}")
                    segment_files.append(segment_path)
                    item.update_status('completed')
                else:
                    print(f"[MERGE] Task {task.task_uuid} - 分段处理失败: {item.original_filename}")
                    item.update_status('failed')
                
                # Update item status
                self.storage.update_video_item(task.task_uuid, item)
            
            # Check if we have segments to merge
            if not segment_files:
                print(f"[MERGE] Task {task.task_uuid} - 没有可用的分段文件，无法合并")
                raise Exception("No valid video segments to merge")
            
            # Merge segments
            print(f"[MERGE] Task {task.task_uuid} - 开始合并所有分段...")
            self.storage.add_merge_log(task.task_uuid, 'info', 'Merging video segments', 'merging')
            task.progress_percentage = 50
            self.storage.save_merge_task(task)
            
            # Create output file path
            output_filename = f"merged_{task.task_uuid}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            # Merge videos
            success = self._merge_video_segments(
                segment_files,
                output_path,
                output_format,
                task.audio_handling
            )
            
            if not success:
                print(f"[MERGE] Task {task.task_uuid} - 合并分段失败")
                raise Exception("Failed to merge video segments")
            
            # Update task with output file path
            task.output_file_path = output_path
            task.status = 'completed'
            task.progress_percentage = 100
            task.completed_at = datetime.now()
            self.storage.save_merge_task(task)
            print(f"[MERGE] Task {task.task_uuid} - 合并完成，输出文件: {output_path}")
            
            # Log completion
            total_time = time.time() - start_time
            self.storage.add_merge_log(task.task_uuid, 'info', 
                                     f'Video merge completed successfully in {total_time:.2f} seconds', 
                                     'completed')
            
            print(f"[MERGE] Task {task.task_uuid} - 总耗时: {total_time:.2f} 秒")
            return True
            
        except Exception as e:
            error_msg = f"Video merge failed: {str(e)}"
            task.status = 'failed'
            task.error_message = error_msg
            self.storage.save_merge_task(task)
            
            self.storage.add_merge_log(task.task_uuid, 'error', error_msg, 'processing_error')
            print(f"[MERGE] Task {task.task_uuid} - 处理异常: {error_msg}")
            return False
    
    def _process_video_segment(self, item: MergeVideoItem, output_dir: str, index: int, 
                             output_format: Dict[str, Any]) -> Optional[str]:
        """Process a video segment based on time selection"""
        try:
            # Create output filename
            segment_filename = f"segment_{index:03d}_{item.item_id}.mp4"
            segment_path = os.path.join(output_dir, segment_filename)
            
            # Check if we need to cut the video
            needs_cutting = (item.start_time > 0 or 
                           (item.end_time is not None and 
                            item.end_time < item.video_duration))
            
            # Check if we need to convert the video
            target_resolution = output_format['resolution']
            current_resolution = item.video_resolution
            target_fps = output_format['fps']
            current_fps = item.fps
            
            needs_conversion = (current_resolution != target_resolution or 
                              abs(current_fps - target_fps) > 1)
            
            # If no cutting or conversion needed, create a symlink or copy
            if not needs_cutting and not needs_conversion:
                # Create a symlink to the original file
                if os.path.exists(segment_path):
                    os.remove(segment_path)
                
                # On Windows, symlinks might require admin privileges, so fall back to copy if needed
                try:
                    os.symlink(item.file_path, segment_path)
                except (OSError, AttributeError):
                    import shutil
                    shutil.copy2(item.file_path, segment_path)
                
                return segment_path
            
            # Build FFmpeg command for cutting and/or conversion
            cmd = ['ffmpeg', '-y']
            
            # Input file
            cmd.extend(['-i', item.file_path])
            
            # Time selection
            if needs_cutting:
                cmd.extend(['-ss', str(item.start_time)])
                if item.end_time is not None:
                    duration = item.end_time - item.start_time
                    cmd.extend(['-t', str(duration)])
            
            # Video settings
            cmd.extend([
                '-c:v', output_format['codec'],
                '-b:v', str(output_format['bitrate']),
                '-preset', 'medium'
            ])
            
            # Resolution conversion if needed
            if needs_conversion:
                cmd.extend(['-vf', f"scale={target_resolution.replace('x', ':')},fps={target_fps}"])
            
            # Audio settings
            if item.has_audio:
                cmd.extend(['-c:a', output_format['audio_codec'], '-b:a', '192k'])
            else:
                cmd.extend(['-an'])  # No audio
            
            # Output file
            cmd.append(segment_path)
            
            # Run FFmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                return None
            
            return segment_path
            
        except Exception as e:
            print(f"Error processing video segment: {e}")
            return None
    
    def _merge_video_segments(self, segment_files: List[str], output_path: str, 
                            output_format: Dict[str, Any], audio_handling: str) -> bool:
        """Merge video segments into a single video using a more reliable method"""
        try:
            if not segment_files:
                return False
            
            print(f"Merging {len(segment_files)} video segments using advanced method")
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Method 1: Try using FFmpeg with concat demuxer and re-encoding
            # This is more reliable than simple concat for videos with different properties
            try:
                # Create a temporary file list for FFmpeg concat
                concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                try:
                    # Write file paths to concat file
                    for file_path in segment_files:
                        concat_file.write(f"file '{file_path}'\n")
                    
                    concat_file.close()
                    
                    # Build FFmpeg command for merging with re-encoding
                    cmd = [
                        'ffmpeg', '-y',
                        '-f', 'concat',
                        '-safe', '0',
                        '-i', concat_file.name,
                        # Force re-encoding to ensure consistent output
                        '-c:v', output_format['codec'],
                        '-b:v', str(output_format['bitrate']),
                        # Ensure consistent frame rate and pixel format
                        '-r', str(output_format['fps']),
                        '-pix_fmt', 'yuv420p'
                    ]
                    
                    # Audio handling with proper resampling
                    if audio_handling == 'remove':
                        cmd.extend(['-an'])  # No audio
                    else:
                        # Force audio resampling to ensure consistency
                        cmd.extend([
                            '-c:a', output_format['audio_codec'],
                            '-ar', '44100',  # Force sample rate to 44.1kHz
                            '-ac', '2',      # Force stereo (2 channels)
                            '-b:a', '192k'
                        ])
                    
                    # Output file
                    cmd.append(output_path)
                    
                    print(f"Running FFmpeg command: {' '.join(cmd)}")
                    
                    # Run FFmpeg command
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
                    
                    if result.returncode != 0:
                        print(f"FFmpeg merge error: {result.stderr}")
                        raise Exception(f"FFmpeg error: {result.stderr}")
                    
                    # Verify the output file exists and has content
                    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                        raise Exception("Output file is empty or does not exist")
                    
                    return True
                    
                finally:
                    # Clean up concat file
                    try:
                        os.unlink(concat_file.name)
                    except:
                        pass
                    
            except Exception as e:
                print(f"Method 1 failed: {e}")
                
                # Method 2: Try using FFmpeg with filter_complex for more control
                try:
                    # Build complex filter command
                    inputs = []
                    filter_complex = []
                    
                    for i, file_path in enumerate(segment_files):
                        inputs.extend(['-i', file_path])
                        filter_complex.append(f"[{i}:v]scale={output_format['resolution'].replace('x', ':')},fps={output_format['fps']},format=yuv420p[v{i}];")
                    
                    # Concatenate video streams
                    for i in range(len(segment_files)):
                        filter_complex.append(f"[v{i}]")
                    
                    filter_complex.append(f"concat=n={len(segment_files)}:v=1:a=0[outv]")
                    
                    # Build FFmpeg command
                    cmd = ['ffmpeg', '-y']
                    cmd.extend(inputs)
                    cmd.extend(['-filter_complex', ''.join(filter_complex)])
                    cmd.extend(['-map', '[outv]'])
                    
                    # Video codec settings
                    cmd.extend([
                        '-c:v', output_format['codec'],
                        '-b:v', str(output_format['bitrate']),
                        '-pix_fmt', 'yuv420p'
                    ])
                    
                    # Audio handling with proper normalization
                    if audio_handling == 'remove':
                        cmd.extend(['-an'])  # No audio
                    elif audio_handling == 'keep_first' and len(segment_files) > 0:
                        # Use only the first video's audio
                        cmd.extend([
                            '-map', '0:a:0',
                            '-c:a', output_format['audio_codec'],
                            '-ar', '44100',  # Force sample rate
                            '-ac', '2',      # Force stereo
                            '-b:a', '192k'
                        ])
                    else:
                        # Properly handle audio concatenation with normalization
                        audio_filter = []
                        audio_inputs = []
                        
                        # Build audio normalization filters
                        for i in range(len(segment_files)):
                            # Normalize each audio stream to consistent format
                            audio_filter.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=1.0[a{i}];")
                            audio_inputs.append(f"[a{i}]")
                        
                        # Concatenate normalized audio streams
                        audio_filter.extend(audio_inputs)
                        audio_filter.append(f"concat=n={len(segment_files)}:v=0:a=1[outa]")
                        
                        # Update filter complex to include audio processing
                        current_filter = cmd[cmd.index('-filter_complex') + 1]
                        cmd[cmd.index('-filter_complex') + 1] = current_filter + ''.join(audio_filter)
                        
                        cmd.extend(['-map', '[outa]'])
                        cmd.extend([
                            '-c:a', output_format['audio_codec'],
                            '-b:a', '192k'
                        ])
                    
                    # Output file
                    cmd.append(output_path)
                    
                    print(f"Running FFmpeg command (Method 2): {' '.join(cmd)}")
                    
                    # Run FFmpeg command
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
                    
                    if result.returncode != 0:
                        print(f"FFmpeg merge error (Method 2): {result.stderr}")
                        raise Exception(f"FFmpeg error (Method 2): {result.stderr}")
                    
                    return True
                    
                except Exception as e:
                    print(f"Method 2 failed: {e}")
                    
                    # Method 3: Simple and reliable approach with explicit audio handling
                    try:
                        return self._merge_video_segments_simple(segment_files, output_path, output_format, audio_handling)
                    except Exception as e3:
                        print(f"Method 3 failed: {e3}")
                        return False
                
        except Exception as e:
            print(f"Error merging video segments: {e}")
            return False
    
    def _merge_video_segments_simple(self, segment_files: List[str], output_path: str, 
                                   output_format: Dict[str, Any], audio_handling: str) -> bool:
        """Simple and reliable video merging method with proper audio handling"""
        try:
            print(f"Using simple merge method for {len(segment_files)} segments")
            
            # Create a temporary file list for FFmpeg concat
            concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            try:
                # Write file paths to concat file
                for file_path in segment_files:
                    concat_file.write(f"file '{file_path}'\n")
                
                concat_file.close()
                
                # Build simple FFmpeg command with proper audio handling
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file.name
                ]
                
                # Video settings - keep it simple but consistent
                cmd.extend([
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',  # Good quality
                    '-pix_fmt', 'yuv420p'
                ])
                
                # Audio settings - force consistency
                if audio_handling == 'remove':
                    cmd.extend(['-an'])
                else:
                    cmd.extend([
                        '-c:a', 'aac',
                        '-ar', '44100',     # Sample rate
                        '-ac', '2',         # Stereo
                        '-b:a', '128k',     # Bitrate
                        '-af', 'aresample=async=1000'  # Audio resampling for sync
                    ])
                
                # Output file
                cmd.append(output_path)
                
                print(f"Running simple FFmpeg command: {' '.join(cmd)}")
                
                # Run FFmpeg command
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
                
                if result.returncode != 0:
                    print(f"Simple FFmpeg merge error: {result.stderr}")
                    return False
                
                # Verify output
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    print("Output file is empty or does not exist")
                    return False
                
                print("Simple merge method completed successfully")
                return True
                
            finally:
                # Clean up concat file
                try:
                    os.unlink(concat_file.name)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error in simple merge method: {e}")
            return False

# Import datetime here to avoid circular import
from datetime import datetime