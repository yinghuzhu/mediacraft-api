"""
用户管理API
处理用户相关的请求
"""
from flask import Blueprint, request, jsonify, g, current_app
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

def get_standard_response(success=True, code=200, message="Success", data=None):
    """生成标准API响应格式"""
    from datetime import datetime
    import uuid
    
    return {
        "success": success,
        "code": code,
        "message": message,
        "data": data or {},
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "v1",
            "request_id": str(uuid.uuid4())
        }
    }

@user_bp.route('/info', methods=['GET'])
def get_user_info():
    """获取用户信息"""
    try:
        # 从会话中获取用户ID
        user_id = getattr(g, 'sid', None)
        
        if not user_id:
            return jsonify(get_standard_response(
                success=False,
                code=401,
                message="未找到有效会话"
            )), 401
        
        # 获取用户管理器
        user_manager = current_app.user_manager
        
        # 获取用户信息
        user_info = user_manager.get_user_info(user_id)
        
        if not user_info:
            return jsonify(get_standard_response(
                success=False,
                code=404,
                message="用户不存在"
            )), 404
        
        return jsonify(get_standard_response(
            data=user_info
        ))
        
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        return jsonify(get_standard_response(
            success=False,
            code=500,
            message="获取用户信息失败"
        )), 500

@user_bp.route('/tasks', methods=['GET'])
def get_user_tasks():
    """获取用户任务列表"""
    try:
        # 从会话中获取用户ID
        user_id = getattr(g, 'sid', None)
        
        if not user_id:
            return jsonify(get_standard_response(
                success=False,
                code=401,
                message="未找到有效会话"
            )), 401
        
        # 获取用户管理器
        user_manager = current_app.user_manager
        
        # 获取用户任务
        user_tasks = user_manager.get_user_tasks(user_id)
        
        # 统计任务状态
        task_stats = {}
        for task in user_tasks:
            status = task.get('status', 'unknown')
            task_stats[status] = task_stats.get(status, 0) + 1
        
        return jsonify(get_standard_response(
            data={
                "tasks": user_tasks,
                "total_count": len(user_tasks),
                "status_stats": task_stats
            }
        ))
        
    except Exception as e:
        logger.error(f"Failed to get user tasks: {e}")
        return jsonify(get_standard_response(
            success=False,
            code=500,
            message="获取用户任务失败"
        )), 500

@user_bp.route('/stats', methods=['GET'])
def get_user_stats():
    """获取用户统计信息"""
    try:
        # 从会话中获取用户ID
        user_id = getattr(g, 'sid', None)
        
        if not user_id:
            return jsonify(get_standard_response(
                success=False,
                code=401,
                message="未找到有效会话"
            )), 401
        
        # 获取用户管理器
        user_manager = current_app.user_manager
        
        # 获取用户信息
        user_info = user_manager.get_user_info(user_id)
        
        if not user_info:
            return jsonify(get_standard_response(
                success=False,
                code=404,
                message="用户不存在"
            )), 404
        
        # 提取统计信息
        stats = {
            "user_id": user_info.get("user_id"),
            "member_since": user_info.get("created_at"),
            "last_active": user_info.get("last_accessed"),
            "total_tasks": user_info.get("task_count", 0),
            "task_breakdown": user_info.get("task_stats", {})
        }
        
        return jsonify(get_standard_response(
            data=stats
        ))
        
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        return jsonify(get_standard_response(
            success=False,
            code=500,
            message="获取用户统计失败"
        )), 500