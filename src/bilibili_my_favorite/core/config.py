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

    # 数据库配置
    DATABASE_PATH: Optional[Path] = "./bilibili_favorites.db"

    # 文件存储配置
    COVERS_DIR: Optional[Path] = "./covers"
    TEMPLATES_DIR: Optional[Path] = "./templates"
    DATA_DIR: Optional[Path] = "./data"
    VIDEOS_DIR: Optional[Path] = "./video_downloads"


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
        base_dir = self.BASE_DIR

        # DATABASE_PATH
        if self.DATABASE_PATH is None:
            self.DATABASE_PATH = base_dir / "bilibili_favorites.db"
        elif not self.DATABASE_PATH.is_absolute():
            self.DATABASE_PATH = (base_dir / self.DATABASE_PATH).resolve()
        else:
            self.DATABASE_PATH = self.DATABASE_PATH.resolve()
        
        # COVERS_DIR
        if self.COVERS_DIR is None:
            self.COVERS_DIR = base_dir / "covers"
        elif not self.COVERS_DIR.is_absolute():
            self.COVERS_DIR = (base_dir / self.COVERS_DIR).resolve()
        else:
            self.COVERS_DIR = self.COVERS_DIR.resolve()

        # TEMPLATES_DIR
        if self.TEMPLATES_DIR is None:
            self.TEMPLATES_DIR = base_dir / "templates"
        elif not self.TEMPLATES_DIR.is_absolute():
            self.TEMPLATES_DIR = (base_dir / self.TEMPLATES_DIR).resolve()
        else:
            self.TEMPLATES_DIR = self.TEMPLATES_DIR.resolve()

        # DATA_DIR
        if self.DATA_DIR is None:
            self.DATA_DIR = base_dir / "data"
        elif not self.DATA_DIR.is_absolute():
            self.DATA_DIR = (base_dir / self.DATA_DIR).resolve()
        else:
            self.DATA_DIR = self.DATA_DIR.resolve()

        # VIDEOS_DIR
        if self.VIDEOS_DIR is None:
            self.VIDEOS_DIR = base_dir / "video_downloads"
        elif not self.VIDEOS_DIR.is_absolute():
            self.VIDEOS_DIR = (base_dir / self.VIDEOS_DIR).resolve()
        else:
            self.VIDEOS_DIR = self.VIDEOS_DIR.resolve()

        # LOG_FILE
        if self.LOG_FILE is None:
            self.LOG_FILE = base_dir / "logs" / "app.log"
        elif not self.LOG_FILE.is_absolute():
            self.LOG_FILE = (base_dir / self.LOG_FILE).resolve()
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
        # These paths are now guaranteed to be Path objects and absolute
        if not self.COVERS_DIR.exists():
             self.COVERS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.DATA_DIR.exists():
             self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.VIDEOS_DIR.exists():
             self.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.LOG_FILE.parent.exists():
             self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


# 创建全局配置实例
config = Config()

# Ensure directories after config is loaded and paths are set.
config.ensure_actual_directories() 