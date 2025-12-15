"""
配置管理模块
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./py_auto_api.db"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 浏览器配置
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30
    
    # 文件存储配置
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # 任务执行配置
    MAX_CONCURRENT_TASKS: int = 5
    TASK_TIMEOUT: int = 300  # 5分钟
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()