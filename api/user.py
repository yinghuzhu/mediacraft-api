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

@user_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(get_standard_response(
                success=False,
                code=400,
                message="请求数据不能为空"
            )), 400
        
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        
        if not username or not password:
            return jsonify(get_standard_response(
                success=False,
                code=400,
                message="用户名和密码不能为空"
            )), 400
        
        # 获取用户管理器
        user_manager = current_app.user_manager
        
        # 注册用户
        result = user_manager.register_user(username, password, email)
        
        if result['success']:
            return jsonify(get_standard_response(
                message="用户注册成功",
                data={"user_id": result['user_id']}
            ))
        else:
            return jsonify(get_standard_response(
                success=False,
                code=400,
                message=result['message']
            )), 400
        
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        return jsonify(get_standard_response(
            success=False,
            code=500,
            message="内部服务器错误"
        )), 500

@user_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(get_standard_response(
                success=False,
                code=400,
                message="请求数据不能为空"
            )), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify(get_standard_response(
                success=False,
                code=400,
                message="用户名和密码不能为空"
            )), 400
        
        # 获取用户管理器和会话管理器
        user_manager = current_app.user_manager
        session_manager = current_app.session_manager
        
        # 验证用户
        auth_result = user_manager.authenticate_user(username, password)
        
        if not auth_result['success']:
            return jsonify(get_standard_response(
                success=False,
                code=401,
                message=auth_result['message']
            )), 401
        
        user_info = auth_result['user']
        
        # 获取当前会话ID（由中间件创建）
        session_id = getattr(g, 'sid', None)
        if not session_id:
            return jsonify(get_standard_response(
                success=False,
                code=500,
                message="会话创建失败"
            )), 500
        
        # 关联用户和会话
        user_manager.associate_user_session(user_info['user_id'], session_id)
        
        # 返回登录成功响应（Cookie由中间件自动设置）
        return jsonify(get_standard_response(
            message="登录成功",
            data={"user": user_info}
        ))
        
    except Exception as e:
        logger.error(f"Failed to login user: {e}")
        return jsonify(get_standard_response(
            success=False,
            code=500,
            message="内部服务器错误"
        )), 500

@user_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    try:
        # 从会话中获取用户ID
        session_id = getattr(g, 'sid', None)
        
        if not session_id:
            return jsonify(get_standard_response(
                success=False,
                code=401,
                message="未找到有效会话"
            )), 401
        
        # 获取用户管理器
        user_manager = current_app.user_manager
        
        # 解除用户会话关联
        user_manager.disassociate_user_session(session_id)
        
        # 清除会话cookie
        response = jsonify(get_standard_response(
            message="登出成功"
        ))
        # 清除cookie时也要考虑domain兼容性
        response.set_cookie(
            'session_id', 
            '', 
            path='/',  # 确保path匹配
            domain=None,  # 不设置domain，确保兼容性
            expires=0,
            httponly=True,
            secure=False,
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to logout user: {e}")
        return jsonify(get_standard_response(
            success=False,
            code=500,
            message="内部服务器错误"
        )), 500

@user_bp.route('/profile', methods=['GET'])
def get_profile():
    """获取用户资料"""
    try:
        # 从会话中获取用户ID
        session_id = getattr(g, 'sid', None)
        
        if not session_id:
            return jsonify(get_standard_response(
                success=False,
                code=401,
                message="未找到有效会话"
            )), 401
        
        # 获取用户管理器
        user_manager = current_app.user_manager
        
        # 获取当前用户
        user_id = user_manager.get_user_by_session(session_id)
        
        if not user_id:
            return jsonify(get_standard_response(
                success=False,
                code=401,
                message="用户未登录"
            )), 401
        
        # 获取用户信息
        user_info = user_manager.get_user_info(user_id)
        
        if not user_info:
            return jsonify(get_standard_response(
                success=False,
                code=404,
                message="用户不存在"
            )), 404
        
        # 获取认证用户信息
        auth_data = user_manager._load_auth_users()
        auth_user_info = None
        
        # 查找对应的认证用户信息
        for username, auth_info in auth_data["auth_users"].items():
            if auth_info["user_id"] == user_id:
                auth_user_info = {
                    "user_id": auth_info["user_id"],
                    "username": auth_info["username"],
                    "email": auth_info.get("email"),
                    "created_at": auth_info["created_at"],
                    "last_login": auth_info.get("last_login")
                }
                break
        
        # 如果找不到认证用户信息，使用基本用户信息
        if not auth_user_info:
            auth_user_info = {
                "user_id": user_id,
                "username": None,
                "email": None,
                "created_at": user_info.get("created_at"),
                "last_login": None
            }
        
        return jsonify(get_standard_response(
            data={"user": auth_user_info}
        ))
        
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        return jsonify(get_standard_response(
            success=False,
            code=500,
            message="获取用户资料失败"
        )), 500

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