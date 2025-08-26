"""
文件管理API
处理文件上传、下载等操作
"""
from flask import Blueprint, request, jsonify, g, send_file
import os
import logging
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

files_bp = Blueprint('files', __name__)

@files_bp.route('/upload', methods=['POST'])
def upload_file():
    """上传文件"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # 验证文件类型
        from flask import current_app
        allowed_extensions = current_app.config_manager.get('allowed_file_types', ['.mp4', '.avi', '.mov'])
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({
                'error': 'File type not allowed',
                'allowed_types': allowed_extensions
            }), 400
        
        # 检查文件大小
        max_size = current_app.config_manager.get('upload_max_size', 100 * 1024 * 1024)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > max_size:
            return jsonify({
                'error': 'File too large',
                'max_size': max_size,
                'file_size': file_size
            }), 413
        
        # 保存文件
        upload_dir = current_app.storage_manager.get_user_upload_dir(sid)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        
        # 如果文件已存在，添加序号
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            name, ext = os.path.splitext(original_path)
            file_path = f"{name}_{counter}{ext}"
            counter += 1
        
        file.save(file_path)
        
        return jsonify({
            'filename': os.path.basename(file_path),
            'file_path': file_path,
            'file_size': file_size,
            'upload_time': os.path.getctime(file_path)
        })
        
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        return jsonify({
            'error': 'File upload failed',
            'message': str(e)
        }), 500

@files_bp.route('/list', methods=['GET'])
def list_files():
    """列出用户上传的文件"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        from flask import current_app
        upload_dir = current_app.storage_manager.get_user_upload_dir(sid)
        
        files = []
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, filename)
                if os.path.isfile(file_path):
                    files.append({
                        'filename': filename,
                        'size': os.path.getsize(file_path),
                        'modified': os.path.getmtime(file_path)
                    })
        
        return jsonify({
            'files': sorted(files, key=lambda x: x['modified'], reverse=True)
        })
        
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        return jsonify({
            'error': 'Failed to list files',
            'message': str(e)
        }), 500

@files_bp.route('/<filename>', methods=['DELETE'])
def delete_file(filename):
    """删除文件"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        from flask import current_app
        upload_dir = current_app.storage_manager.get_user_upload_dir(sid)
        file_path = os.path.join(upload_dir, secure_filename(filename))
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # 检查文件是否正在被任务使用
        user_tasks = current_app.storage_manager.get_user_tasks(sid)
        for task in user_tasks:
            if task.get('status') in ['queued', 'processing']:
                input_path = task.get('input_file_path', '')
                if file_path in input_path or filename in input_path:
                    return jsonify({
                        'error': 'File is being used by an active task',
                        'task_id': task.get('task_id')
                    }), 400
        
        # 删除文件
        os.remove(file_path)
        
        return jsonify({
            'message': f'File {filename} deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        return jsonify({
            'error': 'Failed to delete file',
            'message': str(e)
        }), 500

@files_bp.route('/cleanup', methods=['POST'])
def cleanup_files():
    """清理用户文件"""
    try:
        sid = getattr(g, 'sid', None)
        if not sid:
            return jsonify({'error': 'No valid session'}), 401
        
        from flask import current_app
        
        # 获取清理选项
        cleanup_uploads = request.json.get('cleanup_uploads', False)
        cleanup_results = request.json.get('cleanup_results', False)
        cleanup_completed_only = request.json.get('cleanup_completed_only', True)
        
        deleted_files = []
        
        if cleanup_uploads:
            upload_dir = current_app.storage_manager.get_user_upload_dir(sid)
            if os.path.exists(upload_dir):
                for filename in os.listdir(upload_dir):
                    file_path = os.path.join(upload_dir, filename)
                    if os.path.isfile(file_path):
                        # 检查是否被活跃任务使用
                        can_delete = True
                        if cleanup_completed_only:
                            user_tasks = current_app.storage_manager.get_user_tasks(sid)
                            for task in user_tasks:
                                if task.get('status') in ['queued', 'processing']:
                                    input_path = task.get('input_file_path', '')
                                    if file_path in input_path:
                                        can_delete = False
                                        break
                        
                        if can_delete:
                            os.remove(file_path)
                            deleted_files.append(f"upload/{filename}")
        
        if cleanup_results:
            result_dir = current_app.storage_manager.get_user_result_dir(sid)
            if os.path.exists(result_dir):
                for filename in os.listdir(result_dir):
                    file_path = os.path.join(result_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_files.append(f"result/{filename}")
        
        return jsonify({
            'message': f'Cleanup completed, deleted {len(deleted_files)} files',
            'deleted_files': deleted_files
        })
        
    except Exception as e:
        logger.error(f"Failed to cleanup files: {e}")
        return jsonify({
            'error': 'Failed to cleanup files',
            'message': str(e)
        }), 500