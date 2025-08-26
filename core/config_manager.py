"""
配置管理器
统一管理系统配置
"""
import os
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器 - 统一管理系统配置"""
    
    def __init__(self, storage_manager, flask_config):
        self.storage = storage_manager
        self.flask_config = flask_config
        self._config_cache = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        try:
            # 从存储中加载配置
            stored_config = self.storage.get_config()
            self._config_cache.update(stored_config)
            
            # 从环境变量覆盖配置
            self._load_env_overrides()
            
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
    
    def _load_env_overrides(self):
        """从环境变量加载配置覆盖"""
        env_mappings = {
            'MAX_CONCURRENT_TASKS': 'max_concurrent_tasks',
            'TASK_RETENTION_DAYS': 'task_retention_days',
            'MAX_QUEUE_SIZE': 'max_queue_size',
            'SESSION_TIMEOUT_DAYS': 'session_timeout_days',
            'UPLOAD_MAX_SIZE': 'upload_max_size'
        }
        
        for env_key, config_key in env_mappings.items():
            env_value = os.environ.get(env_key)
            if env_value:
                try:
                    # 尝试转换为整数
                    if env_value.isdigit():
                        self._config_cache[config_key] = int(env_value)
                    else:
                        self._config_cache[config_key] = env_value
                    logger.info(f"Override config {config_key} from environment: {env_value}")
                except ValueError:
                    logger.warning(f"Invalid environment value for {env_key}: {env_value}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config_cache.get(key, default)
    
    def set(self, key: str, value: Any, persist: bool = True):
        """设置配置值"""
        self._config_cache[key] = value
        
        if persist:
            try:
                # 保存到存储
                current_config = self.storage.get_config()
                current_config[key] = value
                self.storage.save_config(current_config)
                logger.info(f"Config {key} updated and persisted: {value}")
            except Exception as e:
                logger.error(f"Failed to persist config {key}: {e}")
    
    def get_all(self) -> Dict:
        """获取所有配置"""
        return self._config_cache.copy()
    
    def update(self, config_dict: Dict, persist: bool = True):
        """批量更新配置"""
        self._config_cache.update(config_dict)
        
        if persist:
            try:
                current_config = self.storage.get_config()
                current_config.update(config_dict)
                self.storage.save_config(current_config)
                logger.info(f"Batch config update persisted: {list(config_dict.keys())}")
            except Exception as e:
                logger.error(f"Failed to persist batch config update: {e}")
    
    def reload(self):
        """重新加载配置"""
        self._config_cache.clear()
        self._load_config()
        logger.info("Configuration reloaded")
    
    def get_flask_config(self, key: str, default: Any = None) -> Any:
        """获取Flask配置"""
        return self.flask_config.get(key, default)
    
    def validate_config(self) -> Dict:
        """验证配置有效性"""
        issues = []
        warnings = []
        
        # 检查必要的配置项
        required_configs = {
            'max_concurrent_tasks': (int, 1, 20),
            'task_retention_days': (int, 1, 365),
            'max_queue_size': (int, 1, 1000),
            'session_timeout_days': (int, 1, 365),
            'upload_max_size': (int, 1024, 1024*1024*1024)  # 1KB to 1GB
        }
        
        for key, (expected_type, min_val, max_val) in required_configs.items():
            value = self.get(key)
            
            if value is None:
                issues.append(f"Missing required config: {key}")
                continue
            
            if not isinstance(value, expected_type):
                issues.append(f"Config {key} should be {expected_type.__name__}, got {type(value).__name__}")
                continue
            
            if isinstance(value, int) and not (min_val <= value <= max_val):
                warnings.append(f"Config {key}={value} is outside recommended range [{min_val}, {max_val}]")
        
        # 检查文件类型配置
        allowed_types = self.get('allowed_file_types', [])
        if not isinstance(allowed_types, list):
            issues.append("Config 'allowed_file_types' should be a list")
        elif not allowed_types:
            warnings.append("No allowed file types configured")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    def get_runtime_info(self) -> Dict:
        """获取运行时配置信息"""
        return {
            "config_source": "JSON file + environment variables",
            "config_file": self.storage.config_file,
            "total_configs": len(self._config_cache),
            "flask_debug": self.flask_config.get('DEBUG', False),
            "data_directory": self.flask_config.get('DATA_DIR', 'data')
        }