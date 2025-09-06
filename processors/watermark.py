"""
水印去除处理器
异步处理视频水印去除任务
"""
import os
import cv2
import numpy as np
from typing import Dict, Callable, Optional
import logging

logger = logging.getLogger(__name__)

class WatermarkProcessor:
    """水印去除处理器"""
    
    def __init__(self, storage_manager):
        self.storage = storage_manager
    
    def process(self, task: Dict, progress_callback: Callable[[int, str], None]) -> str:
        """
        处理水印去除任务
        
        Args:
            task: 任务数据
            progress_callback: 进度回调函数
            
        Returns:
            str: 输出文件路径
        """
        import subprocess
        import tempfile
        
        task_id = task.get('task_id', 'unknown')
        sid = task.get('sid', 'unknown')
        
        logger.info(f"[WATERMARK_PROCESS] Starting watermark removal - task_id: {task_id}, session_id: {sid}")
        logger.info(f"[WATERMARK_PROCESS] Task keys: {list(task.keys())}")
        logger.info(f"[WATERMARK_PROCESS] Full task: {task}")
        
        try:
            input_path = task.get('input_file_path')
            if not input_path or not os.path.exists(input_path):
                logger.error(f"[WATERMARK_PROCESS] Input file not found - task_id: {task_id}, session_id: {sid}, path: {input_path}")
                raise ValueError("Input file not found")
            
            # 获取任务配置
            config = task.get('task_config', {})
            regions = config.get('regions', [])
            
            logger.info(f"[WATERMARK_PROCESS] Task config: {config}")
            logger.info(f"[WATERMARK_PROCESS] Found {len(regions)} regions: {regions}")
            
            if not regions:
                logger.error(f"[WATERMARK_PROCESS] No watermark regions specified - task_id: {task_id}, session_id: {sid}")
                logger.error(f"[WATERMARK_PROCESS] Available task_config keys: {list(config.keys())}")
                raise ValueError("No watermark regions specified in task configuration")
            
            logger.info(f"[WATERMARK_PROCESS] Processing {len(regions)} watermark regions - task_id: {task_id}, session_id: {sid}")
            
            # 准备输出路径
            sid = task.get('sid')
            result_dir = self.storage.get_user_result_dir(sid)
            
            input_filename = os.path.basename(input_path)
            name, ext = os.path.splitext(input_filename)
            output_filename = f"{name}_watermark_removed{ext}"
            output_path = os.path.join(result_dir, output_filename)
            
            progress_callback(10, "开始处理视频...")
            
            # 创建临时文件用于处理
            temp_video_path = os.path.join(tempfile.gettempdir(), f"temp_video_{task.get('task_id', 'unknown')}.mp4")
            
            # 使用OpenCV处理视频帧
            self._process_video_frames(input_path, temp_video_path, regions, progress_callback)
            
            progress_callback(80, "合并音频...")
            
            # 使用FFmpeg合并音频
            self._merge_audio_with_ffmpeg(input_path, temp_video_path, output_path)
            
            # 清理临时文件
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            
            # 验证输出文件
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error(f"[WATERMARK_PROCESS] Output file creation failed - task_id: {task_id}, session_id: {sid}, output_path: {output_path}")
                raise ValueError("Output file creation failed")
            
            progress_callback(100, "水印去除完成")
            logger.info(f"[WATERMARK_PROCESS] Watermark removal completed successfully - task_id: {task_id}, session_id: {sid}, output_path: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"[WATERMARK_PROCESS] Watermark removal failed - task_id: {task_id}, session_id: {sid}, error: {e}")
            # 清理可能的临时和输出文件
            for path in [locals().get('temp_video_path'), locals().get('output_path')]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
            raise
    
    def _process_video_frames(self, input_path: str, output_path: str, regions: list, progress_callback: Callable):
        """处理视频帧"""
        # 打开视频文件
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError("Cannot open video file")
        
        try:
            # 获取视频属性
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            progress_callback(20, f"视频信息: {width}x{height}, {fps:.1f}fps, {total_frames}帧")
            
            # 设置视频编码器 - 使用更好的编码器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                raise ValueError("Cannot create output video file")
            
            frame_count = 0
            
            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # 处理水印区域
                    processed_frame = self._remove_watermark_from_frame(frame, regions)
                    
                    # 写入输出视频
                    out.write(processed_frame)
                    
                    frame_count += 1
                    
                    # 更新进度
                    if frame_count % 30 == 0:  # 每30帧更新一次进度
                        progress = 20 + int((frame_count / total_frames) * 50)
                        progress_callback(progress, f"处理进度: {frame_count}/{total_frames}")
                
                progress_callback(70, "视频帧处理完成")
                
            finally:
                out.release()
                
        finally:
            cap.release()
    
    def _merge_audio_with_ffmpeg(self, input_path: str, video_path: str, output_path: str):
        """使用FFmpeg合并音频"""
        import subprocess
        
        try:
            # 使用FFmpeg命令合并视频和音频
            cmd = [
                'ffmpeg', '-y',  # -y 覆盖输出文件
                '-i', video_path,  # 处理后的视频
                '-i', input_path,  # 原始文件（包含音频）
                '-c:v', 'copy',    # 复制视频流
                '-c:a', 'aac',     # 音频编码为AAC
                '-map', '0:v:0',   # 使用第一个输入的视频流
                '-map', '1:a:0?',  # 使用第二个输入的音频流（如果存在）
                '-shortest',       # 以最短流为准
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.warning(f"FFmpeg failed, trying fallback: {result.stderr}")
                # 如果FFmpeg失败，直接复制处理后的视频
                import shutil
                shutil.copy2(video_path, output_path)
                
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"FFmpeg not available or timeout: {e}")
            # 如果FFmpeg不可用，直接复制处理后的视频
            import shutil
            shutil.copy2(video_path, output_path)
    
    def _remove_watermark_from_frame(self, frame: np.ndarray, regions: list) -> np.ndarray:
        """
        从单帧中去除水印 - 使用稳定版本的算法
        
        Args:
            frame: 输入帧
            regions: 水印区域列表，支持两种格式：
                     - [x1, y1, x2, y2] (旧格式)
                     - {'x': x, 'y': y, 'width': w, 'height': h} (新格式)
            
        Returns:
            np.ndarray: 处理后的帧
        """
        if not regions:
            return frame
        
        # 创建静态掩码 - 这是稳定版本的关键技术
        h, w = frame.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        # 将所有水印区域添加到掩码中
        for region in regions:
            # 处理不同的区域格式
            if isinstance(region, dict):
                # 新格式: {'x': x, 'y': y, 'width': w, 'height': h}
                x = int(region.get('x', 0))
                y = int(region.get('y', 0))
                width = int(region.get('width', 0))
                height = int(region.get('height', 0))
                
                # 确保坐标在有效范围内
                x = max(0, min(x, w))
                y = max(0, min(y, h))
                width = max(0, min(width, w - x))
                height = max(0, min(height, h - y))
                
                if width > 0 and height > 0:
                    # 使用cv2.rectangle填充掩码区域
                    cv2.rectangle(mask, (x, y), (x + width, y + height), 255, -1)
                    
            elif isinstance(region, (list, tuple)) and len(region) == 4:
                # 旧格式: [x1, y1, x2, y2]
                x1, y1, x2, y2 = [int(coord) for coord in region]
                
                # 确保坐标在有效范围内
                x1 = max(0, min(x1, w))
                y1 = max(0, min(y1, h))
                x2 = max(x1, min(x2, w))
                y2 = max(y1, min(y2, h))
                
                if x2 > x1 and y2 > y1:
                    cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
        
        # 使用稳定版本的inpainting算法
        try:
            # 使用INPAINT_NS算法 - 这是稳定版本使用的算法
            inpainted_frame = cv2.inpaint(frame, mask, 3, cv2.INPAINT_NS)
            return inpainted_frame
            
        except Exception as e:
            logger.warning(f"Inpainting failed, using fallback: {e}")
            
            # 如果inpainting失败，使用TELEA算法作为备选
            try:
                inpainted_frame = cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)
                return inpainted_frame
            except Exception as e2:
                logger.warning(f"TELEA inpainting also failed: {e2}")
                
                # 最后的备选方案：对每个区域使用高斯模糊
                result_frame = frame.copy()
                for region in regions:
                    if isinstance(region, dict):
                        x = int(region.get('x', 0))
                        y = int(region.get('y', 0))
                        width = int(region.get('width', 0))
                        height = int(region.get('height', 0))
                        x2 = x + width
                        y2 = y + height
                    elif isinstance(region, (list, tuple)) and len(region) == 4:
                        x, y, x2, y2 = [int(coord) for coord in region]
                    else:
                        continue
                    
                    # 确保坐标有效
                    x = max(0, min(x, w))
                    y = max(0, min(y, h))
                    x2 = max(x, min(x2, w))
                    y2 = max(y, min(y2, h))
                    
                    if x2 > x and y2 > y:
                        # 使用高斯模糊作为最后的备选方案
                        region_data = result_frame[y:y2, x:x2]
                        blurred = cv2.GaussianBlur(region_data, (15, 15), 0)
                        result_frame[y:y2, x:x2] = blurred
                
                return result_frame
    
    def validate_regions(self, regions: list, video_width: int, video_height: int) -> list:
        """
        验证和修正水印区域坐标
        
        Args:
            regions: 原始区域列表，支持两种格式
            video_width: 视频宽度
            video_height: 视频高度
            
        Returns:
            list: 修正后的区域列表（统一为字典格式）
        """
        valid_regions = []
        
        for region in regions:
            try:
                if isinstance(region, dict):
                    # 新格式: {'x': x, 'y': y, 'width': w, 'height': h}
                    x = int(region.get('x', 0))
                    y = int(region.get('y', 0))
                    width = int(region.get('width', 0))
                    height = int(region.get('height', 0))
                    
                    # 修正坐标
                    x = max(0, min(x, video_width))
                    y = max(0, min(y, video_height))
                    width = max(0, min(width, video_width - x))
                    height = max(0, min(height, video_height - y))
                    
                    # 确保区域有效
                    if width > 0 and height > 0:
                        valid_regions.append({
                            'x': x,
                            'y': y,
                            'width': width,
                            'height': height
                        })
                        
                elif isinstance(region, (list, tuple)) and len(region) == 4:
                    # 旧格式: [x1, y1, x2, y2] 转换为新格式
                    x1, y1, x2, y2 = [int(coord) for coord in region]
                    
                    # 修正坐标
                    x1 = max(0, min(x1, video_width))
                    y1 = max(0, min(y1, video_height))
                    x2 = max(x1, min(x2, video_width))
                    y2 = max(y1, min(y2, video_height))
                    
                    # 确保区域有效
                    if x2 > x1 and y2 > y1:
                        valid_regions.append({
                            'x': x1,
                            'y': y1,
                            'width': x2 - x1,
                            'height': y2 - y1
                        })
                        
            except (ValueError, TypeError):
                continue
        
        return valid_regions