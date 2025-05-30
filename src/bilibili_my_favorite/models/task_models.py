"""
任务管理相关数据模型
支持多种类型的长时间运行任务
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union, List
import json
import uuid

# 导入TypedDict类型
from .types import (
    VideoDownloadItemDict, TaskProgressDict, TaskResultDict, 
    TaskStatusDict, VideoInfoDict, BatchDownloadStatsDict
)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 等待执行
    RUNNING = "running"           # 正在执行
    COMPLETED = "completed"       # 执行完成
    FAILED = "failed"             # 执行失败
    CANCELLED = "cancelled"       # 已取消
    PAUSED = "paused"            # 已暂停


class TaskType(Enum):
    """任务类型枚举"""
    VIDEO_DOWNLOAD = "video_download"    # 视频下载
    SYNC_FAVORITES = "sync_favorites"    # 同步收藏夹
    BATCH_DOWNLOAD = "batch_download"    # 批量下载
    EXPORT_DATA = "export_data"          # 数据导出
    IMPORT_DATA = "import_data"          # 数据导入


@dataclass
class TaskProgress:
    """任务进度信息"""
    current: int = 0              # 当前进度
    total: int = 0                # 总进度
    percentage: float = 0.0       # 进度百分比
    message: str = ""             # 进度描述
    sub_tasks: Dict[str, Any] = field(default_factory=dict)  # 子任务进度


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool                 # 是否成功
    data: Optional[Dict[str, Any]] = None  # 结果数据
    error_message: Optional[str] = None    # 错误信息
    error_code: Optional[str] = None       # 错误代码
    output_files: List[str] = field(default_factory=list)  # 输出文件列表
    statistics: Dict[str, Any] = field(default_factory=dict)  # 统计信息


@dataclass
class BaseTask:
    """任务基类"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.VIDEO_DOWNLOAD
    title: str = ""               # 任务标题
    description: str = ""         # 任务描述
    
    # 任务状态
    status: TaskStatus = TaskStatus.PENDING
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Optional[TaskResult] = None
    
    # 任务参数
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 元数据
    priority: int = 0             # 任务优先级（数字越大优先级越高）
    max_retries: int = 3          # 最大重试次数
    retry_count: int = 0          # 当前重试次数
    timeout: Optional[int] = None # 超时时间（秒）
    
    def to_dict(self) -> TaskStatusDict:
        """转换为字典格式"""
        return TaskStatusDict(
            task_id=self.task_id,
            task_type=self.task_type.value,
            title=self.title,
            description=self.description,
            status=self.status.value,
            progress=TaskProgressDict(
                current=self.progress.current,
                total=self.progress.total,
                percentage=self.progress.percentage,
                message=self.progress.message
            ),
            result=TaskResultDict(
                success=self.result.success if self.result else False,
                data=self.result.data if self.result else None,
                error_message=self.result.error_message if self.result else None,
                error_code=self.result.error_code if self.result else None,
                output_files=self.result.output_files if self.result else [],
                statistics=self.result.statistics if self.result else {}
            ) if self.result else None,
            parameters=self.parameters,
            created_at=self.created_at.isoformat(),
            started_at=self.started_at.isoformat() if self.started_at else None,
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            updated_at=self.updated_at.isoformat(),
            priority=self.priority,
            max_retries=self.max_retries,
            retry_count=self.retry_count,
            timeout=self.timeout
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseTask':
        """从字典创建任务实例"""
        task = cls()
        task.task_id = data.get("task_id", task.task_id)
        task.task_type = TaskType(data.get("task_type", TaskType.VIDEO_DOWNLOAD.value))
        task.title = data.get("title", "")
        task.description = data.get("description", "")
        task.status = TaskStatus(data.get("status", TaskStatus.PENDING.value))
        
        # 恢复进度信息
        progress_data = data.get("progress", {})
        task.progress = TaskProgress(
            current=progress_data.get("current", 0),
            total=progress_data.get("total", 0),
            percentage=progress_data.get("percentage", 0.0),
            message=progress_data.get("message", ""),
            sub_tasks=progress_data.get("sub_tasks", {})
        )
        
        # 恢复结果信息
        result_data = data.get("result")
        if result_data:
            task.result = TaskResult(
                success=result_data.get("success", False),
                data=result_data.get("data"),
                error_message=result_data.get("error_message"),
                error_code=result_data.get("error_code"),
                output_files=result_data.get("output_files", []),
                statistics=result_data.get("statistics", {})
            )
        
        task.parameters = data.get("parameters", {})
        
        # 恢复时间信息
        task.created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        task.started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        task.completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        task.updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        
        task.priority = data.get("priority", 0)
        task.max_retries = data.get("max_retries", 3)
        task.retry_count = data.get("retry_count", 0)
        task.timeout = data.get("timeout")
        
        return task


@dataclass
class VideoDownloadTask(BaseTask):
    """视频下载任务"""
    def __init__(self, bvid: str, page: int = 0, quality: int = 80, 
                 output_filename: Optional[str] = None, ffmpeg_path: str = "ffmpeg"):
        super().__init__()
        self.task_type = TaskType.VIDEO_DOWNLOAD
        self.title = f"下载视频 {bvid}"
        self.description = f"下载B站视频 {bvid} P{page+1}"
        self.parameters = {
            "bvid": bvid,
            "page": page,
            "quality": quality,
            "output_filename": output_filename,
            "ffmpeg_path": ffmpeg_path
        }


@dataclass
class SyncFavoritesTask(BaseTask):
    """同步收藏夹任务"""
    def __init__(self, collection_id: Optional[str] = None, force_covers: bool = False):
        super().__init__()
        self.task_type = TaskType.SYNC_FAVORITES
        self.title = "同步收藏夹" if not collection_id else f"同步收藏夹 {collection_id}"
        self.description = "同步B站收藏夹数据到本地数据库"
        self.parameters = {
            "collection_id": collection_id,
            "force_covers": force_covers
        }


@dataclass
class BatchDownloadTask(BaseTask):
    """批量下载任务"""
    def __init__(self, video_list: List[VideoDownloadItemDict], quality: int = 80):
        super().__init__()
        self.task_type = TaskType.BATCH_DOWNLOAD
        self.title = f"批量下载 {len(video_list)} 个视频"
        self.description = f"批量下载 {len(video_list)} 个B站视频"
        self.parameters = {
            "video_list": video_list,
            "quality": quality
        } 