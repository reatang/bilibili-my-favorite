"""
配置管理模块
统一管理应用程序的所有配置项
"""
from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """应用程序配置类"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 项目根目录
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent

    # Docker数据目录 - 统一数据存储目录
    DATA_ROOT: Optional[Path] = None

    # 数据库配置
    DATABASE_PATH: Optional[Path] = None

    # 文件存储配置
    COVERS_DIR: Optional[Path] = None
    TEMPLATES_DIR: Optional[Path] = "./templates"
    DATA_DIR: Optional[Path] = None
    VIDEOS_DIR: Optional[Path] = None
    LOGS_DIR: Optional[Path] = None

    # B站API配置 与原始cookies配置 二选一
    USER_DEDE_USER_ID: Optional[str] = None
    USER_SESSDATA: Optional[str] = None
    USER_BILI_JCT: Optional[str] = None
    USER_BUVID3: Optional[str] = None

    # 原始cookies + SuperCredential 可以获得更高级的功能
    RAW_COOKIES: Optional[str] = None

    # 用户配置
    USER_AC_TIME_VALUE: Optional[str] = None

    # Web服务器配置
    WEB_HOST: str = "127.0.0.1"
    WEB_PORT: int = 8000
    DEBUG: bool = False

    # 下载配置
    DOWNLOAD_TIMEOUT: int = 10
    MAX_PAGES_PER_COLLECTION: int = 100
    REQUEST_DELAY: int = 500 # ms

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[Path] = None

    @model_validator(mode='after')
    def set_default_paths(self) -> 'Config':
        """设置默认路径，支持Docker容器化部署"""
        
        # 确定数据根目录
        # 优先级：环境变量 DATA_ROOT > Docker默认路径 /app/data > 项目根目录
        if self.DATA_ROOT is None:
            # 检查是否在Docker环境中
            docker_data_path = Path("/data")
            if docker_data_path.exists() and Path("/.dockerenv").exists():
                # Docker环境，使用容器内数据目录
                self.DATA_ROOT = docker_data_path
            else:
                # 本地开发环境，使用项目根目录
                self.DATA_ROOT = self.BASE_DIR
        elif not self.DATA_ROOT.is_absolute():
            self.DATA_ROOT = (self.BASE_DIR / self.DATA_ROOT).resolve()
        else:
            self.DATA_ROOT = self.DATA_ROOT.resolve()

        # 设置数据库路径
        if self.DATABASE_PATH is None:
            self.DATABASE_PATH = self.DATA_ROOT / "bilibili_favorites.db"
        elif not self.DATABASE_PATH.is_absolute():
            self.DATABASE_PATH = (self.DATA_ROOT / self.DATABASE_PATH).resolve()
        else:
            self.DATABASE_PATH = self.DATABASE_PATH.resolve()
        
        # 设置封面目录
        if self.COVERS_DIR is None:
            self.COVERS_DIR = self.DATA_ROOT / "covers"
        elif not self.COVERS_DIR.is_absolute():
            self.COVERS_DIR = (self.DATA_ROOT / self.COVERS_DIR).resolve()
        else:
            self.COVERS_DIR = self.COVERS_DIR.resolve()

        # 设置模板目录（相对于项目根目录，不放在数据目录中）
        if self.TEMPLATES_DIR is None:
            self.TEMPLATES_DIR = self.BASE_DIR / "templates"
        elif not self.TEMPLATES_DIR.is_absolute():
            self.TEMPLATES_DIR = (self.BASE_DIR / self.TEMPLATES_DIR).resolve()
        else:
            self.TEMPLATES_DIR = self.TEMPLATES_DIR.resolve()

        # 设置数据临时存储目录
        if self.DATA_DIR is None:
            self.DATA_DIR = self.DATA_ROOT / "data"
        elif not self.DATA_DIR.is_absolute():
            self.DATA_DIR = (self.DATA_ROOT / self.DATA_DIR).resolve()
        else:
            self.DATA_DIR = self.DATA_DIR.resolve()

        # 设置视频下载目录
        if self.VIDEOS_DIR is None:
            self.VIDEOS_DIR = self.DATA_ROOT / "video_downloads"
        elif not self.VIDEOS_DIR.is_absolute():
            self.VIDEOS_DIR = (self.DATA_ROOT / self.VIDEOS_DIR).resolve()
        else:
            self.VIDEOS_DIR = self.VIDEOS_DIR.resolve()

        # 设置日志目录
        if self.LOGS_DIR is None:
            self.LOGS_DIR = self.DATA_ROOT / "logs"
        elif not self.LOGS_DIR.is_absolute():
            self.LOGS_DIR = (self.DATA_ROOT / self.LOGS_DIR).resolve()
        else:
            self.LOGS_DIR = self.LOGS_DIR.resolve()

        # 设置日志文件路径
        if self.LOG_FILE is None:
            self.LOG_FILE = self.LOGS_DIR / "app.log"
        elif not self.LOG_FILE.is_absolute():
            self.LOG_FILE = (self.LOGS_DIR / self.LOG_FILE).resolve()
        else:
            self.LOG_FILE = self.LOG_FILE.resolve()
            
        return self

    @property
    def DATABASE_URL(self) -> str:
        """获取数据库连接URL"""
        if self.DATABASE_PATH is None:
            # This case should ideally not be reached if set_default_paths works correctly
            raise ValueError("DATABASE_PATH is not configured.")
        return f"sqlite:///{self.DATABASE_PATH}"

    def validate_bilibili_credentials(self) -> bool:
        if self.RAW_COOKIES is not None and len(self.RAW_COOKIES) > 0:
            return True
        
        """验证B站凭据是否完整"""
        required_vars = [
            self.USER_DEDE_USER_ID,
            self.USER_SESSDATA,
            self.USER_BILI_JCT,
            self.USER_BUVID3
        ]

        return all(var is not None for var in required_vars)

    def ensure_actual_directories(self) -> None:
        """确保必要的目录存在"""
        # 确保数据根目录存在
        if not self.DATA_ROOT.exists():
            self.DATA_ROOT.mkdir(parents=True, exist_ok=True)
            
        # 确保各个子目录存在
        directories_to_create = [
            self.COVERS_DIR,
            self.DATA_DIR,
            self.VIDEOS_DIR,
            self.LOGS_DIR,
        ]
        
        for directory in directories_to_create:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)

        # 模板目录通常不需要动态创建，但如果不存在也创建
        if not self.TEMPLATES_DIR.exists():
            self.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    def get_data_summary(self) -> dict:
        """获取数据目录配置摘要，用于调试和日志"""
        return {
            "data_root": str(self.DATA_ROOT),
            "database_path": str(self.DATABASE_PATH),
            "covers_dir": str(self.COVERS_DIR),
            "data_dir": str(self.DATA_DIR),
            "videos_dir": str(self.VIDEOS_DIR),
            "logs_dir": str(self.LOGS_DIR),
            "templates_dir": str(self.TEMPLATES_DIR),
            "is_docker_env": Path("/.dockerenv").exists() or str(self.DATA_ROOT).startswith("/app/data")
        }


# 创建全局配置实例
config = Config()

# Ensure directories after config is loaded and paths are set.
config.ensure_actual_directories() 