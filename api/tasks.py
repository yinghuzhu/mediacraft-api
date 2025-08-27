"""
任务管理API
处理异步任务相关的请求
"""
from flask import Blueprint, request, jsonify, g, send_file
import os
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/create', methods=['POST'])
def create_task():
    """创建新任务"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 检查是否可以接受新任务
        from flask import current_app
        can_accept, message = current_app.task_queue_manager.can_accept_task()
        
        if not can_accept:
            return jsonify({
                'error': 'Cannot accept task',
                'message': message
            }), 429
        
        # 获取任务类型
        data = request.get_json()
        task_type = data.get('task_type')
        
        if not task_type:
            return jsonify({'error': 'Missing task_type'}), 400
        
        if task_type not in ['watermark_removal', 'video_merge']:
            return jsonify({'error': 'Invalid task_type'}), 400
        
        # 创建任务记录
        import uuid
        from datetime import datetime, timezone
        
        task_id = str(uuid.uuid4())
        task_data = {
            'task_id': task_id,
            'sid': sid,
            'task_type': task_type,
            'status': 'created',
            'progress_percentage': 0,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'started_at': None,
            'completed_at': None,
            'original_filename': None,
            'file_size': None,
            'input_file_path': None,
            'output_file_path': None,
            'error_message': None,
            'task_config': {}
        }
        
        # 保存任务
        current_app.storage_manager.save_task(task_id, task_data)
        
        # 添加任务到用户
        current_app.user_manager.add_task_to_user(sid, task_id)
        
        logger.info(f"Task created: {task_id}")
        
        return jsonify({
            'success': True,
            'code': 200,
            'message': 'Task created successfully',
            'data': {
                'task_id': task_id,
                'status': 'created',
                'task_type': task_type
            },
            'meta': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': 'v1',
                'request_id': str(uuid.uuid4())
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return jsonify({
            'error': 'Task creation failed',
            'message': str(e)
        }), 500

@tasks_bp.route('/<task_id>/upload', methods=['POST'])
def upload_task_file(task_id):
    """上传文件到指定任务"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        from datetime import datetime, timezone
        import uuid
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        logger.info(f"Task upload - Task SID: {task.get('sid')}, Current SID: {sid}")
        if task.get('sid') != sid:
            logger.error(f"Access denied - Task belongs to {task.get('sid')}, current user is {sid}")
            return jsonify({'error': 'Access denied'}), 403
        
        # 检查任务状态
        if task.get('status') not in ['created', 'uploaded']:
            return jsonify({'error': 'Task cannot accept file upload'}), 400
        
        # 处理文件上传
        if 'file' not in request.files and 'files' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        upload_dir = current_app.storage_manager.get_user_upload_dir(sid)
        
        if task.get('task_type') == 'watermark_removal':
            file = request.files.get('file')
            if not file:
                return jsonify({'error': 'No file for watermark removal'}), 400
            
            # 保存上传文件
            filename = file.filename
            file_path = os.path.join(upload_dir, f"{task_id}_{filename}")
            file.save(file_path)
            
            # 更新任务信息
            task.update({
                'original_filename': filename,
                'input_file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'status': 'uploaded'
            })
            
        elif task.get('task_type') == 'video_merge':
            # 支持单个文件上传（前端一个一个上传）
            file = request.files.get('file')
            if not file:
                return jsonify({'error': 'No file for video merge'}), 400
            
            # 保存上传文件
            filename = file.filename
            file_path = os.path.join(upload_dir, f"{task_id}_{filename}")
            file.save(file_path)
            
            # 初始化task_config如果不存在
            if 'task_config' not in task:
                task['task_config'] = {}
            
            # 分析视频信息
            video_info = _analyze_video_file(file_path)
            
            # 添加文件信息到任务配置
            if 'files' not in task['task_config']:
                task['task_config']['files'] = []
            
            task['task_config']['files'].append({
                'filename': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'duration': video_info.get('duration', 0),
                'resolution': video_info.get('resolution', 'Unknown'),
                'fps': video_info.get('fps', 0),
                'has_audio': video_info.get('has_audio', False),
                'start_time': 0,
                'end_time': video_info.get('duration', 0)
            })
            
            # 更新任务状态
            task['status'] = 'uploaded'
            
            # 计算总文件大小
            total_size = sum(f['size'] for f in task['task_config']['files'])
            filenames = [f['filename'] for f in task['task_config']['files']]
            
            # 更新任务信息
            task.update({
                'original_filename': f"{len(filenames)} files: {', '.join(filenames)}",
                'input_file_path': file_path,  # 最新上传的文件
                'file_size': total_size
            })
        
        # 保存任务
        current_app.storage_manager.save_task(task_id, task)
        
        logger.info(f"File uploaded to task: {task_id}")
        
        return jsonify({
            'success': True,
            'code': 200,
            'message': 'File uploaded successfully',
            'data': {
                'task_id': task_id,
                'status': task.get('status'),
                'original_filename': task.get('original_filename'),
                'file_size': task.get('file_size')
            },
            'meta': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': 'v1',
                'request_id': str(uuid.uuid4())
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to upload file to task {task_id}: {e}")
        return jsonify({
            'error': 'File upload failed',
            'message': str(e)
        }), 500

@tasks_bp.route('/<task_id>/config', methods=['POST'])
def configure_task(task_id):
    """设置任务配置并开始处理"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        from datetime import datetime, timezone
        import uuid
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        if task.get('sid') != sid:
            return jsonify({'error': 'Access denied'}), 403
        
        # 检查任务状态
        if task.get('status') != 'uploaded':
            return jsonify({'error': 'Task must be uploaded before configuration'}), 400
        
        # 获取配置数据
        data = request.get_json()
        config = data.get('config', {})
        
        # 更新任务配置
        if 'task_config' not in task:
            task['task_config'] = {}
        task['task_config'].update(config)
        
        # 提交任务到队列进行处理
        task_queue_id = current_app.task_queue_manager.submit_task(task)
        
        logger.info(f"Task configured and submitted for processing: {task_id} -> {task_queue_id}")
        
        return jsonify({
            'success': True,
            'code': 200,
            'message': 'Task configured and processing started',
            'data': {
                'task_id': task_id,
                'status': 'queued',
                'config': task.get('task_config')
            },
            'meta': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': 'v1',
                'request_id': str(uuid.uuid4())
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to configure task {task_id}: {e}")
        return jsonify({
            'error': 'Task configuration failed',
            'message': str(e)
        }), 500

@tasks_bp.route('/submit', methods=['POST'])
def submit_task():
    """提交任务"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 检查是否可以接受新任务
        from flask import current_app
        can_accept, message = current_app.task_queue_manager.can_accept_task()
        
        if not can_accept:
            return jsonify({
                'error': 'Cannot accept task',
                'message': message
            }), 429  # Too Many Requests
        
        # 获取任务类型
        task_type = request.form.get('task_type')
        if not task_type:
            return jsonify({'error': 'Missing task_type'}), 400
        
        if task_type not in ['watermark_removal', 'video_merge']:
            return jsonify({'error': 'Invalid task_type'}), 400
        
        # 处理文件上传
        if 'file' not in request.files and 'files' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        # 准备任务数据
        task_data = {
            'sid': sid,
            'task_type': task_type,
            'task_config': {}
        }
        
        # 根据任务类型处理不同的参数
        if task_type == 'watermark_removal':
            file = request.files.get('file')
            if not file:
                return jsonify({'error': 'No file for watermark removal'}), 400
            
            # 保存上传文件
            upload_dir = current_app.storage_manager.get_user_upload_dir(sid)
            filename = file.filename
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            task_data.update({
                'original_filename': filename,
                'input_file_path': file_path,
                'file_size': os.path.getsize(file_path)
            })
            
            # 获取水印去除参数
            regions = request.form.get('regions')
            if regions:
                import json
                try:
                    task_data['task_config']['regions'] = json.loads(regions)
                except json.JSONDecodeError:
                    return jsonify({'error': 'Invalid regions format'}), 400
        
        elif task_type == 'video_merge':
            files = request.files.getlist('files')
            if len(files) < 2:
                return jsonify({'error': 'Need at least 2 files for video merge'}), 400
            
            # 保存所有上传文件
            upload_dir = current_app.storage_manager.get_user_upload_dir(sid)
            file_paths = []
            total_size = 0
            
            for file in files:
                filename = file.filename
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                file_paths.append(file_path)
                total_size += os.path.getsize(file_path)
            
            task_data.update({
                'original_filename': f"{len(files)} files",
                'input_file_path': file_paths[0],  # 主文件
                'file_size': total_size,
                'task_config': {
                    'input_files': file_paths
                }
            })
        
        # 提交任务
        task_id = current_app.task_queue_manager.submit_task(task_data)
        
        logger.info(f"Task submitted successfully: {task_id}")
        logger.info(f"Task data: {task_data}")
        
        return jsonify({
            'task_id': task_id,
            'status': 'queued',
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        return jsonify({
            'error': 'Task submission failed',
            'message': str(e)
        }), 500

@tasks_bp.route('/list', methods=['GET'])
def list_tasks():
    """获取任务列表"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取查询参数
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        status_filter = request.args.get('status')
        task_type_filter = request.args.get('type')
        
        # 获取用户任务
        from flask import current_app
        user_tasks = current_app.storage_manager.get_user_tasks(sid)
        
        # 应用过滤器
        if status_filter:
            user_tasks = [task for task in user_tasks if task.get('status') == status_filter]
        
        if task_type_filter:
            user_tasks = [task for task in user_tasks if task.get('task_type') == task_type_filter]
        
        # 分页
        total = len(user_tasks)
        start = (page - 1) * limit
        end = start + limit
        tasks_page = user_tasks[start:end]
        
        # 清理敏感信息
        for task in tasks_page:
            task.pop('task_config', None)  # 移除详细配置
        
        return jsonify({
            'tasks': tasks_page,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        return jsonify({
            'error': 'Failed to list tasks',
            'message': str(e)
        }), 500

@tasks_bp.route('/<task_id>/status', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        if task.get('sid') != sid:
            return jsonify({'error': 'Access denied'}), 403
        
        # 返回任务状态 - 使用统一响应格式
        from datetime import datetime, timezone
        import uuid
        
        response_data = {
            'task_id': task_id,
            'status': task.get('status'),
            'progress_percentage': task.get('progress_percentage', 0),
            'progress_message': task.get('progress_message'),
            'created_at': task.get('created_at'),
            'started_at': task.get('started_at'),
            'completed_at': task.get('completed_at'),
            'error_message': task.get('error_message'),
            'original_filename': task.get('original_filename'),
            'task_type': task.get('task_type'),
            'file_size': task.get('file_size'),
            'input_file_path': task.get('input_file_path'),
            'output_file_path': task.get('output_file_path'),
            'processed_file_path': task.get('output_file_path'),  # 兼容前端
            'config': task.get('task_config', {})
        }
        
        return jsonify({
            "success": True,
            "code": 200,
            "message": "Success",
            "data": response_data,
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "v1",
                "request_id": str(uuid.uuid4())
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return jsonify({
            'error': 'Failed to get task status',
            'message': str(e)
        }), 500

@tasks_bp.route('/<task_id>', methods=['DELETE'])
def cancel_task(task_id):
    """取消任务"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        if task.get('sid') != sid:
            return jsonify({'error': 'Access denied'}), 403
        
        # 尝试取消任务
        success = current_app.task_queue_manager.cancel_task(task_id)
        
        if success:
            return jsonify({
                'task_id': task_id,
                'status': 'cancelled',
                'message': 'Task cancelled successfully'
            })
        else:
            return jsonify({
                'error': 'Cannot cancel task',
                'message': 'Task is already processing or completed'
            }), 400
        
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        return jsonify({
            'error': 'Failed to cancel task',
            'message': str(e)
        }), 500

@tasks_bp.route('/<task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务信息"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        if task.get('sid') != sid:
            return jsonify({'error': 'Access denied'}), 403
        
        # 获取更新数据
        data = request.get_json()
        
        # 初始化帧数据
        frame_data = None
        
        # 更新任务信息
        if 'selected_frame' in data:
            task['selected_frame'] = data['selected_frame']
            task['status'] = 'frame_selected'
            
                        # 获取选中帧的图像数据
            try:
                from processors.video_processor import VideoProcessor
                import cv2
                import base64
                import os
                
                input_file_path = task.get('input_file_path')
                logger.info(f"Input file path: {input_file_path}")
                logger.info(f"File exists: {os.path.exists(input_file_path) if input_file_path else False}")
                
                if input_file_path and os.path.exists(input_file_path):
                    processor = VideoProcessor()
                    logger.info(f"Extracting frame {data['selected_frame']} from {input_file_path}")
                    frame = processor.extract_frame(input_file_path, data['selected_frame'])
                    
                    if frame is not None:
                        logger.info(f"Frame extracted successfully, shape: {frame.shape}")
                        # 将帧转换为base64格式
                        _, buffer = cv2.imencode('.jpg', frame)
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        frame_data = f"data:image/jpeg;base64,{frame_base64}"
                        logger.info(f"Frame converted to base64, length: {len(frame_base64)}")
                    else:
                        logger.error(f"Failed to extract frame {data['selected_frame']} from {input_file_path}")
                else:
                    logger.error(f"Input file path is invalid or file does not exist: {input_file_path}")
                        
            except Exception as e:
                logger.error(f"Error getting frame data: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # 继续执行，不因为帧数据获取失败而中断
        
        if 'regions' in data:
            # 更新水印区域信息
            if 'task_config' not in task:
                task['task_config'] = {}
            task['task_config']['regions'] = data['regions']
            task['status'] = 'regions_selected'
            
            # 如果请求开始处理
            if data.get('action') == 'start_processing':
                # 更新任务状态为queued，让任务队列处理
                task['status'] = 'queued'
                
                # 准备任务数据用于队列处理
                queue_task_data = {
                    'task_id': task_id,  # 使用现有的task_id
                    'sid': task.get('sid'),
                    'task_type': task.get('task_type'),
                    'original_filename': task.get('original_filename'),
                    'input_file_path': task.get('input_file_path'),
                    'file_size': task.get('file_size'),
                    'task_config': task.get('task_config', {}),
                    'status': 'queued',
                    'created_at': task.get('created_at'),
                    'progress_percentage': 0
                }
                
                # 直接将任务添加到队列，不生成新ID
                with current_app.task_queue_manager._task_lock:
                    if len(current_app.task_queue_manager.active_tasks) < current_app.task_queue_manager.max_concurrent:
                        current_app.task_queue_manager._start_task_immediately(task_id)
                    else:
                        current_app.task_queue_manager.task_queue.put(task_id)
                        logger.info(f"Task {task_id} added to queue for processing")
                
                logger.info(f"Task {task_id} queued for processing with regions")
        
        # 保存任务
        current_app.storage_manager.save_task(task_id, task)
        
        response_data = {
            'success': True,
            'task_id': task_id,
            'selected_frame': task.get('selected_frame'),
            'regions': task.get('task_config', {}).get('regions'),
            'status': task.get('status'),
            'message': 'Task updated successfully'
        }
        
        # 如果有帧数据，添加到响应中
        if frame_data is not None:
            response_data['frame_data'] = frame_data
            logger.info(f"Frame data added to response for task {task_id}")
        else:
            logger.warning(f"No frame data available for task {task_id}")
            
        logger.info(f"Response data: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        return jsonify({
            'error': 'Failed to update task',
            'message': str(e)
        }), 500

@tasks_bp.route('/<task_id>/frames', methods=['GET'])
def get_task_frames(task_id):
    """获取任务视频的帧图片"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        logger.info(f"Looking for task frames: {task_id}")
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            logger.error(f"Task not found: {task_id}")
            # 列出所有任务以便调试
            all_tasks = current_app.storage_manager.get_tasks()
            logger.info(f"Available tasks: {list(all_tasks.get('tasks', {}).keys())}")
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        logger.info(f"Task sid: {task.get('sid')}, Current sid: {sid}")
        if task.get('sid') != sid:
            logger.error(f"Access denied - Task belongs to {task.get('sid')}, current user is {sid}")
            return jsonify({'error': 'Access denied'}), 403
        
        # 获取视频文件路径
        input_file_path = task.get('input_file_path')
        if not input_file_path or not os.path.exists(input_file_path):
            return jsonify({'error': 'Video file not found'}), 404
        
        # 提取视频帧
        import cv2
        import base64
        
        cap = cv2.VideoCapture(input_file_path)
        if not cap.isOpened():
            return jsonify({'error': 'Cannot open video file'}), 500
        
        try:
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # 获取请求的帧数量
            count = int(request.args.get('count', 12))
            
            frames = []
            if total_frames > 0:
                # 计算要提取的帧索引
                step = max(1, total_frames // count)
                frame_indices = list(range(0, total_frames, step))[:count]
                
                for i, frame_index in enumerate(frame_indices):
                    # 跳转到指定帧
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    ret, frame = cap.read()
                    
                    if ret:
                        # 调整图片大小以减少数据量
                        height, width = frame.shape[:2]
                        if width > 400:
                            scale = 400 / width
                            new_width = 400
                            new_height = int(height * scale)
                            frame = cv2.resize(frame, (new_width, new_height))
                        
                        # 转换为JPEG格式
                        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        
                        # 转换为base64
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        image_data = f"data:image/jpeg;base64,{frame_base64}"
                        
                        frames.append({
                            'index': i,
                            'frame_number': frame_index,
                            'timestamp': frame_index / fps if fps > 0 else 0,
                            'image_data': image_data
                        })
            
            return jsonify({
                'frames': frames,
                'total_frames': len(frames),
                'video_info': {
                    'total_frames': total_frames,
                    'fps': fps,
                    'duration': total_frames / fps if fps > 0 else 0
                }
            })
            
        finally:
            cap.release()
        
    except Exception as e:
        logger.error(f"Failed to get task frames: {e}")
        return jsonify({
            'error': 'Failed to get video frames',
            'message': str(e)
        }), 500

@tasks_bp.route('/<task_id>/thumbnail', methods=['GET'])
def get_task_thumbnail(task_id):
    """获取任务视频的缩略图（第一帧）"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        if task.get('sid') != sid:
            return jsonify({'error': 'Access denied'}), 403
        
        # 获取输入文件路径
        input_file_path = task.get('input_file_path')
        if not input_file_path or not os.path.exists(input_file_path):
            return jsonify({'error': 'Video file not found'}), 404
        
        # 提取第一帧
        import cv2
        import base64
        from io import BytesIO
        
        cap = cv2.VideoCapture(input_file_path)
        if not cap.isOpened():
            return jsonify({'error': 'Cannot open video file'}), 500
        
        try:
            # 智能提取缩略图：寻找第一个非黑屏帧
            frame = _extract_smart_thumbnail(cap)
            if frame is None:
                return jsonify({'error': 'Cannot extract valid thumbnail'}), 500
            
            # 调整图片大小
            height, width = frame.shape[:2]
            if width > 200:
                scale = 200 / width
                new_width = 200
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # 转换为JPEG格式
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # 返回图片数据
            from flask import Response
            return Response(
                buffer.tobytes(),
                mimetype='image/jpeg',
                headers={
                    'Cache-Control': 'public, max-age=3600',
                    'Content-Disposition': f'inline; filename="thumbnail_{task_id}.jpg"'
                }
            )
            
        finally:
            cap.release()
        
    except Exception as e:
        logger.error(f"Failed to get task thumbnail: {e}")
        return jsonify({
            'error': 'Failed to get thumbnail',
            'message': str(e)
        }), 500

@tasks_bp.route('/<task_id>/files/<int:file_index>/thumbnail', methods=['GET'])
def get_file_thumbnail(task_id, file_index):
    """获取任务中特定文件的缩略图（第一帧）"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        if task.get('sid') != sid:
            return jsonify({'error': 'Access denied'}), 403
        
        # 获取文件列表
        files = task.get('task_config', {}).get('files', [])
        if file_index < 0 or file_index >= len(files):
            return jsonify({'error': 'File index out of range'}), 404
        
        # 获取文件路径
        file_info = files[file_index]
        file_path = file_info.get('path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Video file not found'}), 404
        
        # 提取第一帧
        import cv2
        import base64
        from io import BytesIO
        
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return jsonify({'error': 'Cannot open video file'}), 500
        
        try:
            # 智能提取缩略图：寻找第一个非黑屏帧
            frame = _extract_smart_thumbnail(cap)
            if frame is None:
                return jsonify({'error': 'Cannot extract valid thumbnail'}), 500
            
            # 调整图片大小
            height, width = frame.shape[:2]
            if width > 200:
                scale = 200 / width
                new_width = 200
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # 转换为JPEG格式
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # 返回图片数据
            from flask import Response
            return Response(
                buffer.tobytes(),
                mimetype='image/jpeg',
                headers={
                    'Cache-Control': 'public, max-age=3600',
                    'Content-Disposition': f'inline; filename="thumbnail_{task_id}_{file_index}.jpg"'
                }
            )
            
        finally:
            cap.release()
        
    except Exception as e:
        logger.error(f"Failed to get file thumbnail: {e}")
        return jsonify({
            'error': 'Failed to get thumbnail',
            'message': str(e)
        }), 500

@tasks_bp.route('/<task_id>/download', methods=['GET'])
def download_result(task_id):
    """下载任务结果"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        if task.get('sid') != sid:
            return jsonify({'error': 'Access denied'}), 403
        
        # 检查任务状态
        if task.get('status') != 'completed':
            return jsonify({
                'error': 'Task not completed',
                'status': task.get('status')
            }), 400
        
        # 检查结果文件
        output_path = task.get('output_file_path')
        if not output_path or not os.path.exists(output_path):
            return jsonify({'error': 'Result file not found'}), 404
        
        # 发送文件
        filename = os.path.basename(output_path)
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"processed_{filename}"
        )
        
    except Exception as e:
        logger.error(f"Failed to download result: {e}")
        return jsonify({
            'error': 'Failed to download result',
            'message': str(e)
        }), 500

def _analyze_video_file(file_path: str) -> dict:
    """分析视频文件信息"""
    try:
        import cv2
        import subprocess
        import json
        
        # 使用OpenCV获取基本信息
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return {'duration': 0, 'resolution': 'Unknown', 'fps': 0, 'has_audio': False}
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        # 使用FFprobe检查音频流
        has_audio = _check_audio_stream(file_path)
        
        return {
            'duration': duration,
            'resolution': f"{width}x{height}",
            'fps': fps,
            'has_audio': has_audio
        }
    except Exception as e:
        logger.error(f"Failed to analyze video file {file_path}: {e}")
        return {'duration': 0, 'resolution': 'Unknown', 'fps': 0, 'has_audio': False}

def _extract_smart_thumbnail(cap):
    """智能提取视频缩略图，避免黑屏和空白帧"""
    try:
        import cv2
        import numpy as np
        
        # 获取视频信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            return None
        
        # 定义要尝试的帧位置（百分比）
        positions = [0.1, 0.2, 0.3, 0.15, 0.25, 0.05, 0.4, 0.5, 0]  # 最后尝试第一帧
        
        best_frame = None
        best_score = 0
        
        for pos_ratio in positions:
            frame_pos = int(total_frames * pos_ratio)
            if frame_pos >= total_frames:
                continue
            
            # 跳转到指定帧
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            
            if not ret or frame is None:
                continue
            
            # 计算帧的质量分数
            score = _calculate_frame_quality(frame)
            
            # 如果找到高质量帧，直接返回
            if score > 80:  # 高质量阈值
                return frame
            
            # 记录最佳帧
            if score > best_score:
                best_score = score
                best_frame = frame.copy()
        
        return best_frame
        
    except Exception as e:
        logger.error(f"Error in smart thumbnail extraction: {e}")
        # 如果智能提取失败，尝试返回第一帧
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            return frame if ret else None
        except:
            return None

def _calculate_frame_quality(frame):
    """计算帧的质量分数，用于选择最佳缩略图"""
    try:
        import cv2
        import numpy as np
        
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. 亮度检查（避免过暗或过亮的帧）
        mean_brightness = np.mean(gray)
        brightness_score = 0
        if 30 <= mean_brightness <= 200:  # 理想亮度范围
            brightness_score = 40
        elif 20 <= mean_brightness <= 220:  # 可接受范围
            brightness_score = 20
        else:
            brightness_score = 0
        
        # 2. 对比度检查（避免平坦的图像）
        contrast = np.std(gray)
        contrast_score = min(contrast / 2, 30)  # 最高30分
        
        # 3. 边缘检查（有更多细节的帧更好）
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        edge_score = min(edge_density * 100, 30)  # 最高30分
        
        total_score = brightness_score + contrast_score + edge_score
        return total_score
        
    except Exception as e:
        logger.error(f"Error calculating frame quality: {e}")
        return 0

def _check_audio_stream(file_path: str) -> bool:
    """检查视频是否有音频流"""
    try:
        import subprocess
        import json
        
        cmd = [
            'ffprobe', 
            '-v', 'error', 
            '-select_streams', 'a:0', 
            '-show_entries', 'stream=codec_type', 
            '-of', 'json', 
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return False
        
        data = json.loads(result.stdout)
        return 'streams' in data and len(data['streams']) > 0
    except Exception:
        return False

@tasks_bp.route('/<task_id>/segments/<int:segment_index>', methods=['PUT'])
def update_segment_time(task_id, segment_index):
    """更新视频片段的时间范围"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        # 获取任务
        from flask import current_app
        task = current_app.storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 验证任务所有权
        if task.get('sid') != sid:
            return jsonify({'error': 'Access denied'}), 403
        
        # 获取请求数据
        data = request.get_json()
        start_time = data.get('start_time', 0)
        end_time = data.get('end_time')
        
        # 更新片段时间
        if 'task_config' in task and 'files' in task['task_config']:
            files = task['task_config']['files']
            if 0 <= segment_index < len(files):
                files[segment_index]['start_time'] = start_time
                if end_time is not None:
                    files[segment_index]['end_time'] = end_time
                
                # 保存任务
                current_app.storage_manager.save_task(task_id, task)
                
                return jsonify({
                    'success': True,
                    'code': 200,
                    'message': 'Segment time updated successfully',
                    'data': files[segment_index]
                })
        
        return jsonify({'error': 'Invalid segment index'}), 400
        
    except Exception as e:
        logger.error(f"Failed to update segment time: {e}")
        return jsonify({
            'error': 'Failed to update segment time',
            'message': str(e)
        }), 500