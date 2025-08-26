"""
MediaCraft 异步任务管理系统
Flask主应用程序
"""
import os
import sys
import logging

# 添加当前目录到Python路径 - 必须在其他导入之前
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, g
from flask_cors import CORS

from core.env_config import get_config

# 导入核心组件
from core.storage import FileStorageManager
from core.session import SessionManager, create_session_middleware
from core.task_queue import TaskQueueManager
from core.config_manager import ConfigManager
from core.user_manager import UserManager

# 导入API蓝图
from api.session import session_bp
from api.tasks import tasks_bp
from api.files import files_bp
from api.user import user_bp

# 导入视频处理器
from processors.watermark import WatermarkProcessor
from processors.merger import VideoMerger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """应用工厂函数"""
    app = Flask(__name__)

    config = get_config()
    
    # 使用新的配置系统
    app.config.update(config.get_flask_config())
    
    # 添加其他配置
    app.config['DATA_DIR'] = config.DATA_DIR
    app.config['CORS_ORIGINS'] = config.CORS_ORIGINS
    
    # 初始化CORS
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         supports_credentials=True)
    
    # 初始化核心组件
    storage_manager = FileStorageManager(config.DATA_DIR)
    session_manager = SessionManager(storage_manager)
    config_manager = ConfigManager(storage_manager, app.config)
    user_manager = UserManager(storage_manager)
    task_queue_manager = TaskQueueManager(
        storage_manager, 
        max_concurrent=config.MAX_CONCURRENT_TASKS
    )
    
    # 注册任务执行器
    watermark_processor = WatermarkProcessor(storage_manager)
    video_merger = VideoMerger(storage_manager)
    
    task_queue_manager.register_task_executor('watermark_removal', watermark_processor.process)
    task_queue_manager.register_task_executor('video_merge', video_merger.process)
    
    # 将组件添加到应用上下文
    app.storage_manager = storage_manager
    app.session_manager = session_manager
    app.config_manager = config_manager
    app.user_manager = user_manager
    app.task_queue_manager = task_queue_manager
    
    # 应用会话中间件
    session_middleware = create_session_middleware(session_manager)
    session_middleware(app)
    
    # 注册API蓝图
    app.register_blueprint(session_bp, url_prefix='/api/session')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(files_bp, url_prefix='/api/files')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册系统路由
    register_system_routes(app)
    
    logger.info("MediaCraft异步任务系统启动完成")
    return app

def register_error_handlers(app):
    """注册错误处理器"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': '请求参数错误'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'error': 'Unauthorized',
            'message': '未授权访问'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'error': 'Forbidden',
            'message': '禁止访问'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': '资源不存在'
        }), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'error': 'Request Entity Too Large',
            'message': '上传文件过大'
        }), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': '服务器内部错误'
        }), 500

def register_system_routes(app):
    """注册系统路由"""
    
    @app.route('/')
    def index():
        """系统首页"""
        return jsonify({
            'name': 'MediaCraft异步任务系统',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'session': '/api/session',
                'tasks': '/api/tasks',
                'files': '/api/files',
                'system': '/api/system'
            }
        })
    
    @app.route('/api/system/status')
    def system_status():
        """系统状态"""
        try:
            queue_status = app.task_queue_manager.get_queue_status()
            session_stats = app.session_manager.get_session_stats()
            storage_stats = app.storage_manager.get_storage_stats()
            
            return jsonify({
                'status': 'healthy',
                'queue': queue_status,
                'sessions': session_stats,
                'storage': storage_stats,
                'config': {
                    'max_concurrent_tasks': app.config_manager.get('max_concurrent_tasks'),
                    'max_queue_size': app.config_manager.get('max_queue_size'),
                    'task_retention_days': app.config_manager.get('task_retention_days')
                }
            })
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/system/config')
    def system_config():
        """系统配置"""
        try:
            config_info = app.config_manager.get_all()
            runtime_info = app.config_manager.get_runtime_info()
            validation = app.config_manager.validate_config()
            
            return jsonify({
                'config': config_info,
                'runtime': runtime_info,
                'validation': validation
            })
        except Exception as e:
            logger.error(f"Failed to get system config: {e}")
            return jsonify({
                'error': str(e)
            }), 500
    
    @app.route('/health')
    def health_check():
        """健康检查"""
        return jsonify({
            'status': 'healthy',
            'timestamp': app.storage_manager._load_json('', {}).get('timestamp', 'unknown')
        })

# 应用清理函数
def cleanup_app(app):
    """应用清理"""
    try:
        if hasattr(app, 'task_queue_manager'):
            app.task_queue_manager.shutdown()
        logger.info("Application cleanup completed")
    except Exception as e:
        logger.error(f"Error during application cleanup: {e}")

if __name__ == '__main__':
    # 创建应用
    app = create_app()
    
    try:
        # 启动应用
        config = get_config()
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        cleanup_app(app)