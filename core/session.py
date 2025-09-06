"""
会话管理器
基于Cookie的用户会话管理系统
"""
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """会话管理器 - 管理用户会话和Cookie"""
    
    def __init__(self, storage_manager):
        self.storage = storage_manager
        self.session_timeout = timedelta(days=30)
    
    def generate_sid(self) -> str:
        """生成安全的会话ID"""
        return secrets.token_urlsafe(32)
    
    def create_session(self, request, user_agent: str = "", ip_address: str = "") -> str:
        """创建新会话"""
        try:
            sid = self.generate_sid()
            now = datetime.utcnow().isoformat()
            
            session_data = {
                "sid": sid,
                "created_at": now,
                "last_accessed": now,
                "is_active": True,
                "user_agent": user_agent or request.headers.get('User-Agent', ''),
                "ip_address": ip_address or request.remote_addr or ''
            }
            
            # 保存会话数据
            self.storage.save_session(sid, session_data)
            
            # 创建用户专用目录
            self.storage.get_user_upload_dir(sid)
            self.storage.get_user_result_dir(sid)
            
            logger.info(f"[SESSION_CREATE] Created new session - session_id: {sid}, IP: {session_data.get('ip_address')}, User-Agent: {session_data.get('user_agent')[:50]}...")
            return sid
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def validate_session(self, sid: str) -> bool:
        """验证会话有效性"""
        if not sid:
            return False
        
        try:
            session = self.storage.get_session(sid)
            
            if not session or not session.get("is_active"):
                return False
            
            # 检查会话是否过期
            last_accessed_str = session.get("last_accessed", "")
            if last_accessed_str:
                try:
                    last_accessed = datetime.fromisoformat(last_accessed_str)
                    if datetime.utcnow() - last_accessed > self.session_timeout:
                        logger.info(f"[SESSION_VALIDATE] Session expired - session_id: {sid}, last_accessed: {last_accessed_str}")
                        self.deactivate_session(sid)
                        return False
                except ValueError:
                    logger.warning(f"Invalid last_accessed format for session {sid}")
                    return False
            
            # 更新最后访问时间
            session["last_accessed"] = datetime.utcnow().isoformat()
            self.storage.save_session(sid, session)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate session {sid}: {e}")
            return False
    
    def get_or_create_session(self, request) -> str:
        """获取或创建会话"""
        try:
            # 从Cookie中获取SID
            sid = request.cookies.get('session_id')
            
            # 验证现有会话
            if sid and self.validate_session(sid):
                return sid
            
            # 创建新会话
            return self.create_session(request)
            
        except Exception as e:
            logger.error(f"Failed to get or create session: {e}")
            # 如果出错，创建新会话
            return self.create_session(request)
    
    def get_session_info(self, sid: str) -> Optional[Dict]:
        """获取会话信息"""
        try:
            session = self.storage.get_session(sid)
            if session and self.validate_session(sid):
                return session
            return None
        except Exception as e:
            logger.error(f"Failed to get session info for {sid}: {e}")
            return None
    
    def deactivate_session(self, sid: str) -> bool:
        """停用会话"""
        try:
            session = self.storage.get_session(sid)
            if session:
                session["is_active"] = False
                session["deactivated_at"] = datetime.utcnow().isoformat()
                self.storage.save_session(sid, session)
                logger.info(f"Deactivated session: {sid}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to deactivate session {sid}: {e}")
            return False
    
    def delete_session(self, sid: str) -> bool:
        """删除会话"""
        try:
            result = self.storage.delete_session(sid)
            if result:
                logger.info(f"Deleted session: {sid}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete session {sid}: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            sessions = self.storage.get_sessions()
            expired_count = 0
            cutoff_time = datetime.utcnow() - self.session_timeout
            
            for sid, session in list(sessions["sessions"].items()):
                last_accessed_str = session.get("last_accessed", "")
                if last_accessed_str:
                    try:
                        last_accessed = datetime.fromisoformat(last_accessed_str)
                        if last_accessed < cutoff_time:
                            self.delete_session(sid)
                            expired_count += 1
                    except ValueError:
                        # 无效的时间格式，删除会话
                        self.delete_session(sid)
                        expired_count += 1
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
    
    def get_active_sessions_count(self) -> int:
        """获取活跃会话数量"""
        try:
            sessions = self.storage.get_sessions()
            active_count = 0
            
            for session in sessions["sessions"].values():
                if session.get("is_active") and self.validate_session(session.get("sid")):
                    active_count += 1
            
            return active_count
        except Exception as e:
            logger.error(f"Failed to get active sessions count: {e}")
            return 0
    
    def get_session_stats(self) -> Dict:
        """获取会话统计信息"""
        try:
            sessions = self.storage.get_sessions()
            total_sessions = len(sessions["sessions"])
            active_sessions = 0
            
            # 统计活跃会话
            for session in sessions["sessions"].values():
                if session.get("is_active"):
                    active_sessions += 1
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "inactive_sessions": total_sessions - active_sessions
            }
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "inactive_sessions": 0
            }

def create_session_middleware(session_manager: SessionManager):
    """创建会话中间件"""
    def middleware(app):
        @app.before_request
        def before_request():
            from flask import request, g, current_app
            
            # 获取或创建会话
            g.sid = session_manager.get_or_create_session(request)
            g.session_info = session_manager.get_session_info(g.sid)
            
            # 确保用户记录存在
            if hasattr(current_app, 'user_manager') and g.sid:
                g.user = current_app.user_manager.get_or_create_user(g.sid)
        
        @app.after_request
        def after_request(response):
            from flask import g, request
            
            # 只在以下情况设置会话Cookie：
            # 1. 新创建的会话（没有现有cookie或cookie无效）
            # 2. 登录成功后
            # 3. 会话初始化请求
            should_set_cookie = False
            
            if hasattr(g, 'sid') and g.sid:
                existing_sid = request.cookies.get('session_id')
                
                # 如果没有现有cookie，或者现有cookie与当前会话不匹配，则设置新cookie
                if not existing_sid or existing_sid != g.sid:
                    should_set_cookie = True
                
                # 如果是登录请求成功，也设置cookie
                if request.endpoint == 'user.login' and response.status_code == 200:
                    should_set_cookie = True
                
                # 如果是会话初始化请求，也设置cookie
                if request.path == '/api/session/init':
                    should_set_cookie = True
                
                if should_set_cookie:
                    # 获取请求的host，处理localhost和127.0.0.1的兼容性
                    host = request.headers.get('Host', 'localhost:50001')
                    domain = None
                    
                    # 如果是localhost或127.0.0.1，不设置domain让cookie在两者间共享
                    if 'localhost' in host or '127.0.0.1' in host:
                        domain = None  # 不设置domain，使用默认行为
                    
                    response.set_cookie(
                        'session_id', 
                        g.sid,
                        path='/',  # 明确设置为根路径
                        domain=domain,  # 动态设置domain
                        max_age=30 * 24 * 60 * 60,  # 30天
                        httponly=True,
                        secure=False,  # 开发环境设为False，生产环境应为True
                        samesite='Lax'
                    )
            
            return response
    
    return middleware