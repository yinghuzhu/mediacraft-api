"""
异步任务管理系统配置文件
"""
import os
from datetime import timedelta

class Config:
    """基础配置"""
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # 数据存储配置
    DATA_DIR = os.environ.get('DATA_DIR') or os.path.join(os.path.dirname(__file__), 'data')
    TEMP_DIR = os.environ.get('TEMP_DIR') or os.path.join(DATA_DIR, 'temp')
    
    # 确保目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
    RESULTS_DIR = os.path.join(DATA_DIR, 'results')
    STORAGE_DIR = os.path.join(DATA_DIR, 'storage')

    # 任务队列配置
    MAX_CONCURRENT_TASKS = 3
    MAX_QUEUE_SIZE = 50
    TASK_RETENTION_DAYS = 7
    
    # 会话配置
    SESSION_TIMEOUT = timedelta(days=30)
    COOKIE_NAME = 'sid'
    COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30天
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}
    
    # CORS配置
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-please-change'

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# 使用惰性加载方式，避免模块初始化时的问题
_current_config = None
_config_name = None

def get_config_name():
    """获取配置名称"""
    global _config_name
    if _config_name is None:
        _config_name = os.environ.get('FLASK_ENV', 'default')
    return _config_name

def get_current_config():
    """获取当前环境的配置实例"""
    global _current_config
    if _current_config is None:
        config_name = get_config_name()
        _current_config = config[config_name]()
    return _current_config