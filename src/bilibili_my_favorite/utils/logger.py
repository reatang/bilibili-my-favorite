"""
日志工具模块
提供统一的日志记录功能
"""
import logging
import sys
from pathlib import Path
from typing import Optional
# from ..core.config import config  # 延迟导入避免循环依赖


def setup_logger(
    name: str = "bilibili_favorites",
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    设置并返回日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    if level is None:
        try:
            from ..core.config import config
            log_level = config.LOG_LEVEL
        except ImportError:
            log_level = "INFO"
    else:
        log_level = level
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_path = log_file
    else:
        try:
            from ..core.config import config
            file_path = config.LOG_FILE
        except ImportError:
            file_path = None
    
    if file_path:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 创建默认日志记录器
logger = setup_logger() 