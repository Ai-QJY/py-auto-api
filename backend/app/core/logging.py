"""
日志配置模块
"""

import sys
from loguru import logger
from app.core.config import settings


def setup_logging():
    """配置日志系统"""
    
    # 清除默认处理器
    logger.remove()
    
    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO" if not settings.DEBUG else "DEBUG",
        colorize=True
    )
    
    # 文件输出
    logger.add(
        "logs/py_auto_api.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8"
    )
    
    # 错误日志
    logger.add(
        "logs/errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )
    
    logger.info("日志系统初始化完成")