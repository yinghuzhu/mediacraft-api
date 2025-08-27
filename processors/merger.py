"""
视频合并处理器
异步处理视频合并任务
"""
import os
import cv2
import numpy as np
from typing import Dict, Callable, List
import logging

logger = logging.getLogger(__name__)

class VideoMerger:
    """视频合并处理器"""
    
    def __init__(self, storage_manager):
        self.storage = storage_manager
    
    def process(self, task: Dict, progress_callback: Callable[[int, str], None]) -> str:
        """
        处理视频合并任务
        
        Args:
            task: 任务数据
            progress_callback: 进度回调函数
            
        Returns:
            str: 输出文件路径
        """
        try:
            # 获取输入文件列表
            config = task.get('task_config', {})
            
            # 支持多种数据格式
            files_data = []
            input_files = []
            
            # 1. 检查segments格式（前端发送的格式）
            segments = config.get('segments', [])
            if segments:
                # 从任务中获取上传的文件信息
                task_files = task.get('files', [])
                for segment in segments:
                    filename = segment.get('filename')
                    # 根据文件名找到对应的文件路径
                    for task_file in task_files:
                        if task_file.get('original_filename') == filename:
                            file_info = {
                                'path': task_file.get('file_path'),
                                'start_time': segment.get('startTime', 0),
                                'end_time': segment.get('endTime'),
                                'duration': task_file.get('duration', 0)
                            }
                            files_data.append(file_info)
                            input_files.append(task_file.get('file_path'))
                            break
            
            # 2. 检查files格式（新格式）
            elif config.get('files'):
                files_data = config.get('files', [])
                input_files = [f.get('path') for f in files_data if f.get('path')]
                logger.info(f"Files format - files_data count: {len(files_data)}, input_files count: {len(input_files)}")
                logger.info(f"Files data: {files_data}")
            
            # 3. 检查input_files格式（旧格式）
            else:
                input_files = config.get('input_files', [])
                files_data = [{'path': f} for f in input_files]
                logger.info(f"Input files format - input_files count: {len(input_files)}")
            
            logger.info(f"Final input_files count: {len(input_files)}")
            if len(input_files) < 2:
                raise ValueError(f"Video merge requires at least 2 input files, got {len(input_files)}")
            
            # 验证所有输入文件存在
            for file_path in input_files:
                if not os.path.exists(file_path):
                    raise ValueError(f"Input file not found: {file_path}")
            
            progress_callback(10, f"开始合并 {len(input_files)} 个视频文件...")
            
            # 准备输出路径
            sid = task.get('sid')
            result_dir = self.storage.get_user_result_dir(sid)
            output_filename = f"merged_video_{len(input_files)}_files.mp4"
            output_path = os.path.join(result_dir, output_filename)
            
            # 分析所有输入视频的属性
            video_info = self._analyze_videos(input_files)
            progress_callback(20, f"分析完成，目标分辨率: {video_info['width']}x{video_info['height']}")
            
            # 执行合并（传递文件信息而不是路径列表）
            self._merge_videos(files_data, output_path, video_info, progress_callback)
            
            # 验证输出文件
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise ValueError("Output file creation failed")
            
            progress_callback(100, "视频合并完成")
            logger.info(f"Video merge completed: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Video merge failed: {e}")
            # 清理可能的输出文件
            if 'output_path' in locals() and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            raise
    
    def _analyze_videos(self, input_files: List[str]) -> Dict:
        """
        分析输入视频的属性
        
        Args:
            input_files: 输入文件列表
            
        Returns:
            Dict: 视频属性信息
        """
        video_infos = []
        
        for file_path in input_files:
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                cap.release()
                raise ValueError(f"Cannot open video file: {file_path}")
            
            info = {
                'path': file_path,
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
            }
            video_infos.append(info)
            cap.release()
        
        # 确定输出视频的属性
        # 使用最常见的分辨率
        resolutions = [(info['width'], info['height']) for info in video_infos]
        target_resolution = max(set(resolutions), key=resolutions.count)
        
        # 使用最常见的帧率
        fps_values = [info['fps'] for info in video_infos]
        target_fps = max(set(fps_values), key=fps_values.count)
        
        return {
            'width': target_resolution[0],
            'height': target_resolution[1],
            'fps': target_fps,
            'video_infos': video_infos,
            'total_frames': sum(info['frame_count'] for info in video_infos)
        }
    
    def _merge_videos(self, input_files: List[str], output_path: str, 
                     video_info: Dict, progress_callback: Callable[[int, str], None]):
        """
        执行视频合并（支持时间段切割，参考稳定分支实现）
        
        Args:
            input_files: 输入文件列表（实际是files数据）
            output_path: 输出文件路径
            video_info: 视频属性信息
            progress_callback: 进度回调函数
        """
        import subprocess
        import tempfile
        
        try:
            progress_callback(30, "准备处理视频片段...")
            
            # 创建临时片段文件列表
            segment_files = []
            temp_dir = tempfile.mkdtemp()
            
            try:
                # 处理每个视频片段
                for i, file_info in enumerate(input_files):
                    file_path = file_info.get('path')
                    start_time = file_info.get('start_time', 0)
                    end_time = file_info.get('end_time')
                    duration = file_info.get('duration', 0)
                    
                    if not file_path or not os.path.exists(file_path):
                        raise ValueError(f"Video file not found: {file_path}")
                    
                    progress_callback(
                        30 + int((i / len(input_files)) * 40),
                        f"处理片段 {i+1}/{len(input_files)}: {os.path.basename(file_path)}"
                    )
                    
                    # 创建临时片段文件
                    segment_filename = f"segment_{i:03d}.mp4"
                    segment_path = os.path.join(temp_dir, segment_filename)
                    
                    # 检查是否需要切割
                    needs_cutting = (start_time > 0 or (end_time and end_time < duration))
                    
                    if needs_cutting:
                        # 使用FFmpeg切割视频片段（强制重新编码以避免时间戳问题）
                        cmd = ['ffmpeg', '-y', '-i', file_path]
                        
                        if start_time > 0:
                            cmd.extend(['-ss', str(start_time)])
                        
                        if end_time and end_time > start_time:
                            cmd.extend(['-t', str(end_time - start_time)])
                        
                        # 强制重新编码而不是copy，确保时间戳准确
                        cmd.extend([
                            '-c:v', 'libx264',
                            '-preset', 'medium',
                            '-crf', '23',
                            '-pix_fmt', 'yuv420p',
                            '-c:a', 'aac',
                            '-ar', '44100',
                            '-ac', '2',
                            '-b:a', '128k',
                            segment_path
                        ])
                        
                        logger.info(f"Cutting segment: {' '.join(cmd)}")
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        
                        if result.returncode != 0:
                            logger.error(f"FFmpeg cutting failed: {result.stderr}")
                            raise ValueError(f"Failed to cut segment {i+1}: {result.stderr}")
                    else:
                        # 不需要切割，创建符号链接或复制
                        import shutil
                        shutil.copy2(file_path, segment_path)
                    
                    segment_files.append(segment_path)
                
                progress_callback(70, "开始合并视频片段...")
                
                # 创建concat文件
                concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                try:
                    for segment_path in segment_files:
                        concat_file.write(f"file '{segment_path}'\n")
                    
                    concat_file.close()
                    
                    # 使用FFmpeg合并片段（参考稳定版本的逻辑）
                    cmd = [
                        'ffmpeg', '-y',
                        '-f', 'concat',
                        '-safe', '0',
                        '-i', concat_file.name,
                        '-c:v', 'libx264',
                        '-preset', 'medium',
                        '-crf', '23',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac',
                        '-ar', '44100',     # 强制采样率
                        '-ac', '2',         # 强制立体声
                        '-b:a', '128k',
                        '-af', 'aresample=async=1000',  # 音频重采样确保同步
                        output_path
                    ]
                    
                    logger.info(f"Merging segments: {' '.join(cmd)}")
                    
                    progress_callback(80, "执行FFmpeg合并...")
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    
                    if result.returncode != 0:
                        logger.error(f"FFmpeg merge failed: {result.stderr}")
                        raise ValueError(f"FFmpeg merge failed: {result.stderr}")
                    
                    progress_callback(90, "FFmpeg合并完成，正在验证...")
                    
                    # 验证输出文件
                    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                        raise ValueError("Output file is empty or does not exist")
                    
                    logger.info(f"Video merge completed successfully: {output_path}")
                    
                finally:
                    # 清理concat文件
                    try:
                        os.unlink(concat_file.name)
                    except:
                        pass
                
            finally:
                # 清理临时片段文件
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Video merge failed: {e}")
            raise
    
    def _merge_videos_fallback(self, input_files: List[str], output_path: str, 
                              progress_callback: Callable[[int, str], None]) -> bool:
        """
        备用视频合并方法（使用copy编解码器）
        """
        import subprocess
        import tempfile
        
        try:
            progress_callback(65, "使用备用方法合并...")
            
            # 创建临时文件列表
            concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            try:
                # 写入文件路径到concat文件
                for file_path in input_files:
                    concat_file.write(f"file '{file_path}'\n")
                
                concat_file.close()
                
                # 使用copy编解码器（更快，保持原始质量）
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file.name,
                    '-c', 'copy',  # 复制流，不重新编码
                    output_path
                ]
                
                logger.info(f"Fallback FFmpeg command: {' '.join(cmd)}")
                
                # 执行FFmpeg命令
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    logger.error(f"Fallback FFmpeg failed: {result.stderr}")
                    raise ValueError(f"Fallback FFmpeg merge failed: {result.stderr}")
                
                # 验证输出文件
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise ValueError("Fallback output file is empty or does not exist")
                
                logger.info("Fallback merge method completed successfully")
                return True
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(concat_file.name)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Fallback merge method failed: {e}")
            raise
    
    def validate_input_files(self, input_files: List[str]) -> Dict:
        """
        验证输入文件
        
        Args:
            input_files: 输入文件列表
            
        Returns:
            Dict: 验证结果
        """
        issues = []
        warnings = []
        valid_files = []
        
        if len(input_files) < 2:
            issues.append("Need at least 2 files for video merge")
            return {
                'valid': False,
                'issues': issues,
                'warnings': warnings,
                'valid_files': valid_files
            }
        
        for file_path in input_files:
            if not os.path.exists(file_path):
                issues.append(f"File not found: {file_path}")
                continue
            
            # 检查文件是否为有效视频
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                issues.append(f"Cannot open video file: {file_path}")
                cap.release()
                continue
            
            # 获取视频信息
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            cap.release()
            
            if width <= 0 or height <= 0:
                issues.append(f"Invalid video dimensions: {file_path}")
                continue
            
            if fps <= 0:
                warnings.append(f"Invalid frame rate in: {file_path}")
            
            if frame_count <= 0:
                warnings.append(f"No frames found in: {file_path}")
            
            valid_files.append({
                'path': file_path,
                'width': width,
                'height': height,
                'fps': fps,
                'frame_count': frame_count
            })
        
        return {
            'valid': len(issues) == 0 and len(valid_files) >= 2,
            'issues': issues,
            'warnings': warnings,
            'valid_files': valid_files
        }