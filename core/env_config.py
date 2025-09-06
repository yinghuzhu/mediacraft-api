"""
环境配置管理器
支持从 .env 文件加载配置
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import timedelta

logger = logging.getLogger(__name__)

class EnvConfigLoader:
    """环境配置加载器"""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file
        self.config_cache: Dict[str, Any] = {}
        self._load_env_file()
    
    def _load_env_file(self):
        """加载 .env 文件"""
        if not self.env_file:
            # 自动检测环境文件
            env = os.environ.get('FLASK_ENV', 'development')
            self.env_file = f'.env.{env}'
        
        if os.path.exists(self.env_file):
            logger.info(f"Loading configuration from {self.env_file}")
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # 移除引号
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # 设置环境变量（如果尚未设置）
                        if key not in os.environ:
                            os.environ[key] = value
                            
            logger.info(f"Configuration loaded from {self.env_file}")
        else:
            logger.warning(f"Environment file {self.env_file} not found, using defaults")
    
    def get_str(self, key: str, default: str = '') -> str:
        """获取字符串配置"""
        return os.environ.get(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        try:
            return int(os.environ.get(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default {default}")
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = os.environ.get(key, '').lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        elif value in ('false', '0', 'no', 'off'):
            return False
        return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return float(os.environ.get(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid float value for {key}, using default {default}")
            return default
    
    def get_list(self, key: str, default: list = None, separator: str = ',') -> list:
        """获取列表配置"""
        if default is None:
            default = []
        
        value = os.environ.get(key, '')
        if not value:
            return default
        
        return [item.strip() for item in value.split(separator) if item.strip()]

class EnhancedConfig:
    """增强的配置类"""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_loader = EnvConfigLoader(env_file)
        self._setup_config()
    
    def _setup_config(self):
        """设置配置"""
        # 环境检测
        self.FLASK_ENV = self.env_loader.get_str('FLASK_ENV', 'development')
        self.IS_PRODUCTION = self.FLASK_ENV == 'production'
        
        # Flask 配置
        self.SECRET_KEY = self.env_loader.get_str('SECRET_KEY', 'dev-secret-key-change-in-production')
        self.DEBUG = self.env_loader.get_bool('FLASK_DEBUG', False)
        
        # 生产环境安全检查
        if self.IS_PRODUCTION and self.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError("Production environment requires a secure SECRET_KEY")
        
        # 服务器配置
        self.HOST = self.env_loader.get_str('HOST', '127.0.0.1')
        self.PORT = self.env_loader.get_int('PORT', 50001)
        
        # 数据目录配置
        self.DATA_DIR = self.env_loader.get_str('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.TEMP_DIR = self.env_loader.get_str('TEMP_DIR', os.path.join(self.DATA_DIR, 'temp'))
        self.UPLOAD_DIR = self.env_loader.get_str('UPLOAD_DIR', os.path.join(self.DATA_DIR, 'uploads'))
        self.RESULTS_DIR = self.env_loader.get_str('RESULTS_DIR', os.path.join(self.DATA_DIR, 'results'))
        self.STORAGE_DIR = self.env_loader.get_str('STORAGE_DIR', os.path.join(self.DATA_DIR, 'storage'))
        
        # 确保目录存在
        for directory in [self.DATA_DIR, self.TEMP_DIR, self.UPLOAD_DIR, self.RESULTS_DIR, self.STORAGE_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        # 日志目录
        log_dir = os.path.join(self.DATA_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 任务队列配置
        self.MAX_CONCURRENT_TASKS = self.env_loader.get_int('MAX_CONCURRENT_TASKS', 3)
        self.MAX_QUEUE_SIZE = self.env_loader.get_int('MAX_QUEUE_SIZE', 50)
        self.TASK_RETENTION_DAYS = self.env_loader.get_int('TASK_RETENTION_DAYS', 7)
        self.TASK_TIMEOUT_SECONDS = self.env_loader.get_int('TASK_TIMEOUT_SECONDS', 1800)
        
        # 会话配置
        self.SESSION_TIMEOUT = timedelta(days=30)
        self.COOKIE_NAME = 'sid'
        self.COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30天
        
        # 安全配置
        self.SESSION_COOKIE_SECURE = self.env_loader.get_bool('SESSION_COOKIE_SECURE', False)
        self.SESSION_COOKIE_HTTPONLY = self.env_loader.get_bool('SESSION_COOKIE_HTTPONLY', True)
        self.SESSION_COOKIE_SAMESITE = self.env_loader.get_str('SESSION_COOKIE_SAMESITE', 'Lax')
        
        # 文件上传配置
        self.MAX_CONTENT_LENGTH = self.env_loader.get_int('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)  # 100MB
        self.UPLOAD_TIMEOUT = self.env_loader.get_int('UPLOAD_TIMEOUT', 300)
        self.PROCESSING_TIMEOUT = self.env_loader.get_int('PROCESSING_TIMEOUT', 1800)
        self.ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}
        
        # CORS配置
        cors_origins = self.env_loader.get_list('CORS_ORIGINS', [
            'http://localhost:3000', 
            'http://127.0.0.1:3000',
            'http://mediacraft.yzhu.name'
        ])
        self.CORS_ORIGINS = cors_origins
        self.ENABLE_CORS = self.env_loader.get_bool('ENABLE_CORS', True)
        
        # 日志配置
        self.LOG_LEVEL = self.env_loader.get_str('LOG_LEVEL', 'INFO')
        self.LOG_FILE = self.env_loader.get_str('LOG_FILE', os.path.join(log_dir, 'app.log'))
        
        # 监控配置
        self.ENABLE_METRICS = self.env_loader.get_bool('ENABLE_METRICS', False)
        self.HEALTH_CHECK_INTERVAL = self.env_loader.get_int('HEALTH_CHECK_INTERVAL', 60)
        
        # 开发工具配置
        self.ENABLE_DEBUG_TOOLBAR = self.env_loader.get_bool('ENABLE_DEBUG_TOOLBAR', False)
        
        # 生产环境优化 - 在所有配置加载完成后执行
        if self.IS_PRODUCTION:
            self._setup_production_optimizations()
    
    def _setup_production_optimizations(self):
        """设置生产环境优化"""
        # 强制关闭调试模式
        self.DEBUG = False
        self.ENABLE_DEBUG_TOOLBAR = False
        
        # 增强安全设置
        self.SESSION_COOKIE_SECURE = True
        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = 'Strict'
        
        # 性能优化
        if self.MAX_CONCURRENT_TASKS < 2:
            self.MAX_CONCURRENT_TASKS = 2  # 生产环境最少2个并发
        
        # 日志级别
        if self.LOG_LEVEL == 'DEBUG':
            self.LOG_LEVEL = 'INFO'  # 生产环境不使用DEBUG级别
        
        logger.info("Production environment optimizations applied")
    
    def get_flask_config(self) -> dict:
        """获取 Flask 应用配置"""
        return {
            'SECRET_KEY': self.SECRET_KEY,
            'DEBUG': self.DEBUG,
            'MAX_CONTENT_LENGTH': self.MAX_CONTENT_LENGTH,
            'SESSION_COOKIE_SECURE': self.SESSION_COOKIE_SECURE,
            'SESSION_COOKIE_HTTPONLY': self.SESSION_COOKIE_HTTPONLY,
            'SESSION_COOKIE_SAMESITE': self.SESSION_COOKIE_SAMESITE,
        }
    
    def __repr__(self):
        return f"<EnhancedConfig env_file={self.env_loader.env_file}>"

# 全局配置实例
_config_instance = None

def get_config(env_file: Optional[str] = None) -> EnhancedConfig:
    """获取配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = EnhancedConfig(env_file)
    return _config_instance

def reload_config(env_file: Optional[str] = None):
    """重新加载配置"""
    global _config_instance
    _config_instance = EnhancedConfig(env_file)
    return _config_instance