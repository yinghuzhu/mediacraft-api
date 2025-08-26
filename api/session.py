"""
会话管理API
处理用户会话相关的请求
"""
from flask import Blueprint, request, jsonify, g
import logging

logger = logging.getLogger(__name__)

session_bp = Blueprint('session', __name__)

@session_bp.route('/init', methods=['GET'])
def init_session():
    """初始化会话"""
    try:
        # 会话已经在中间件中创建
        sid = getattr(g, 'sid', None)
        session_info = getattr(g, 'session_info', None)
        
        if not sid:
            return jsonify({
                'error': 'Failed to initialize session'
            }), 500
        
        # 检查是否是新创建的会话
        is_new_session = session_info and session_info.get('created_at') == session_info.get('last_accessed')
        
        return jsonify({
            'sid': sid,
            'created': is_new_session,
            'session_info': {
                'created_at': session_info.get('created_at') if session_info else None,
                'last_accessed': session_info.get('last_accessed') if session_info else None
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to initialize session: {e}")
        return jsonify({
            'error': 'Session initialization failed',
            'message': str(e)
        }), 500

@session_bp.route('/validate', methods=['GET'])
def validate_session():
    """验证会话"""
    try:
        sid = getattr(g, 'sid', None)
        session_info = getattr(g, 'session_info', None)
        
        if not sid or not session_info:
            return jsonify({
                'valid': False,
                'message': 'No valid session found'
            }), 401
        
        return jsonify({
            'valid': True,
            'sid': sid,
            'session_info': {
                'created_at': session_info.get('created_at'),
                'last_accessed': session_info.get('last_accessed'),
                'is_active': session_info.get('is_active', False)
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to validate session: {e}")
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 500

@session_bp.route('/info', methods=['GET'])
def session_info():
    """获取会话详细信息"""
    try:
        sid = getattr(g, 'sid', None)
        session_info = getattr(g, 'session_info', None)
        
        if not sid or not session_info:
            return jsonify({
                'error': 'No valid session found'
            }), 401
        
        # 获取用户任务统计
        from flask import current_app
        user_tasks = current_app.storage_manager.get_user_tasks(sid)
        
        task_stats = {}
        for task in user_tasks:
            status = task.get('status', 'unknown')
            task_stats[status] = task_stats.get(status, 0) + 1
        
        return jsonify({
            'sid': sid,
            'session_info': session_info,
            'task_stats': {
                'total_tasks': len(user_tasks),
                'status_breakdown': task_stats
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@session_bp.route('/logout', methods=['POST'])
def logout():
    """注销会话"""
    try:
        sid = getattr(g, 'sid', None)
        
        if not sid:
            return jsonify({
                'message': 'No active session to logout'
            })
        
        # 停用会话
        from flask import current_app
        success = current_app.session_manager.deactivate_session(sid)
        
        if success:
            return jsonify({
                'message': 'Session logged out successfully'
            })
        else:
            return jsonify({
                'message': 'Session logout failed'
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to logout session: {e}")
        return jsonify({
            'error': str(e)
        }), 500