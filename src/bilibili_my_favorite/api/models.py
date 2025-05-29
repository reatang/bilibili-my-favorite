"""
API数据模型
定义请求和响应的Pydantic模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CollectionResponse(BaseModel):
    """收藏夹响应模型"""
    id: int
    bilibili_fid: str
    title: str
    user_mid: str
    user_name: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    media_count: int = 0
    last_synced: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class VideoResponse(BaseModel):
    """视频响应模型"""
    id: int
    bilibili_id: str
    bvid: str
    title: str
    cover_url: Optional[str] = None
    local_cover_path: Optional[str] = None
    intro: Optional[str] = None
    duration: int = 0
    uploader_name: str
    uploader_mid: str
    uploader_face: Optional[str] = None
    fav_time: Optional[int] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    first_seen: datetime
    last_seen: datetime


class VideoDetailResponse(VideoResponse):
    """视频详细信息响应模型"""
    type: int = 2
    page_count: int = 1
    attr: int = 0
    ctime: Optional[int] = None
    pubtime: Optional[int] = None
    first_cid: Optional[str] = None
    season_info: Optional[str] = None
    ogv_info: Optional[str] = None
    link: Optional[str] = None
    media_list_link: Optional[str] = None
    uploader_jump_link: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CollectionStatsResponse(BaseModel):
    """收藏夹统计信息响应模型"""
    total_videos: int = 0
    available_videos: int = 0
    deleted_videos: int = 0
    last_video_seen: Optional[datetime] = None


class SyncStatsResponse(BaseModel):
    """同步统计信息响应模型"""
    collections_processed: int = 0
    videos_added: int = 0
    videos_updated: int = 0
    videos_deleted: int = 0
    covers_downloaded: int = 0
    errors: List[str] = []


class SyncRequest(BaseModel):
    """同步请求模型"""
    collection_id: Optional[str] = Field(None, description="指定收藏夹ID，为空则同步所有")
    force_download_covers: bool = Field(False, description="是否强制重新下载封面")


class VideoSearchRequest(BaseModel):
    """视频搜索请求模型"""
    status: Optional[str] = Field("all", pattern="^(all|available|deleted)$")
    search: Optional[str] = Field(None, min_length=1, max_length=100)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """成功响应模型"""
    message: str
    data: Optional[Any] = None 