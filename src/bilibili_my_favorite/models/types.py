"""
类型定义文件
使用TypedDict提供更好的类型安全性和代码可读性
"""
from typing import TypedDict, Optional, List, Any, Union
from datetime import datetime


# =============================================================================
# 视频相关类型
# =============================================================================

class VideoInfoDict(TypedDict):
    """视频信息字典类型"""
    title: str
    uploader: str
    duration: int
    page: int
    page_title: str


class VideoPageDict(TypedDict):
    """视频分P信息字典类型"""
    cid: int
    part: str
    duration: int
    dimension: dict


class BilibiliVideoInfoDict(TypedDict):
    """B站视频完整信息字典类型"""
    bvid: str
    title: str
    duration: int
    owner: dict  # {"name": str, "mid": int}
    pages: List[VideoPageDict]


class VideoDownloadItemDict(TypedDict):
    """批量下载中的视频项字典类型"""
    bvid: str
    page: Optional[int]
    title: Optional[str]
    quality: Optional[int]


class DownloadResultDict(TypedDict):
    """下载结果字典类型"""
    bvid: str
    success: bool
    output_file: Optional[str]
    error: Optional[str]


# =============================================================================
# 任务相关类型
# =============================================================================

class TaskProgressDict(TypedDict):
    """任务进度字典类型"""
    current: int
    total: int
    percentage: float
    message: str


class TaskResultDict(TypedDict):
    """任务结果字典类型"""
    success: bool
    data: Optional[dict]
    error_message: Optional[str]
    error_code: Optional[str]
    output_files: List[str]
    statistics: dict


class TaskStatusDict(TypedDict):
    """任务状态字典类型"""
    task_id: str
    task_type: str
    title: str
    status: str
    progress: TaskProgressDict
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[TaskResultDict]


class TaskStatisticsDict(TypedDict):
    """任务统计字典类型"""
    status_distribution: dict
    type_distribution: dict
    today_tasks: int
    total_tasks: int


class QueueInfoDict(TypedDict):
    """队列信息字典类型"""
    pending_count: int
    running_count: int
    pending_by_type: dict
    estimated_wait_time: int


class SystemStatusDict(TypedDict):
    """系统状态字典类型"""
    executor: dict
    statistics: TaskStatisticsDict
    timestamp: str


# =============================================================================
# 同步相关类型
# =============================================================================

class SyncStatsDict(TypedDict):
    """同步统计字典类型"""
    collections_processed: int
    videos_added: int
    videos_updated: int
    videos_deleted: int
    covers_downloaded: int
    deleted_videos: List[dict]
    errors: List[str]


class CollectionStatsDict(TypedDict):
    """收藏夹统计字典类型"""
    total_videos: int
    available_videos: int
    deleted_videos: int


class VideoTypeStatsDict(TypedDict):
    """视频类型统计字典类型"""
    official_videos: int
    normal_videos: int


class GlobalStatsDict(TypedDict):
    """全局统计字典类型"""
    total_collections: int
    total_videos: int
    available_videos: int
    deleted_videos: int


# =============================================================================
# 数据库相关类型
# =============================================================================

class CollectionDict(TypedDict):
    """收藏夹字典类型"""
    id: int
    bilibili_fid: str
    title: str
    description: str
    media_count: int
    is_public: bool
    cover_url: Optional[str]
    last_synced: Optional[str]
    created_at: str
    updated_at: str


class VideoDict(TypedDict):
    """视频字典类型"""
    id: int
    bvid: str
    title: str
    description: str
    uploader_name: str
    uploader_mid: int
    duration: int
    pub_date: str
    cover_url: Optional[str]
    view_count: Optional[int]
    danmaku_count: Optional[int]
    reply_count: Optional[int]
    favorite_count: Optional[int]
    coin_count: Optional[int]
    share_count: Optional[int]
    like_count: Optional[int]
    is_deleted: bool
    delete_reason: Optional[str]
    video_type: str
    last_seen: Optional[str]
    created_at: str
    updated_at: str


class DeletedVideoDict(TypedDict):
    """被删除视频字典类型"""
    title: str
    bvid: str
    collection_title: str


# =============================================================================
# API相关类型
# =============================================================================

class APIResponseDict(TypedDict):
    """API响应字典类型"""
    success: bool
    message: str
    data: Optional[Any]


class TaskListResponseDict(TypedDict):
    """任务列表响应字典类型"""
    tasks: List[TaskStatusDict]
    total: int


class ActiveTasksResponseDict(TypedDict):
    """活跃任务响应字典类型"""
    tasks: List[TaskStatusDict]
    total: int


class CurrentTaskResponseDict(TypedDict):
    """当前任务响应字典类型"""
    current_task: Optional[TaskStatusDict]


# =============================================================================
# 下载服务相关类型
# =============================================================================

class DownloadStreamDict(TypedDict):
    """下载流字典类型"""
    streams: List[Any]
    detecter: Any
    download_data: dict


class VideoDownloadInfoDict(TypedDict):
    """视频下载信息字典类型"""
    bvid: str
    title: str
    uploader: str
    duration: int
    pages: int
    current_page: dict
    available_qualities: List[int]


class BatchDownloadStatsDict(TypedDict):
    """批量下载统计字典类型"""
    total_videos: int
    successful_downloads: int
    failed_downloads: int 