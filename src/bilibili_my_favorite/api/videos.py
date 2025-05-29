"""
视频API路由
处理视频相关的HTTP请求
"""
import math
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from ..dao.video_dao import video_dao
from ..dao.collection_dao import collection_dao
from .models import (
    VideoResponse, VideoDetailResponse, PaginatedResponse,
    ErrorResponse, SuccessResponse
)
from ..utils.logger import logger

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("/collections/{collection_id}", response_model=PaginatedResponse, summary="获取收藏夹中的视频")
async def get_videos_by_collection(
    collection_id: int,
    status: Optional[str] = Query("all", pattern="^(all|available|deleted)$", description="视频状态过滤"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取指定收藏夹中的视频列表
    
    - status: all(全部), available(可用), deleted(已删除)
    - search: 在视频标题和UP主名称中搜索
    - page: 页码，从1开始
    - page_size: 每页视频数量，最大100
    """
    try:
        # 检查收藏夹是否存在
        collection = await collection_dao.get_collection_by_id(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail=f"收藏夹 {collection_id} 不存在")
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取视频列表
        videos = await video_dao.get_videos_by_collection(
            collection_id=collection_id,
            status=status,
            search=search,
            limit=page_size,
            offset=offset
        )
        
        # 获取总数（为了分页信息，需要单独查询）
        total_videos = await video_dao.get_videos_by_collection(
            collection_id=collection_id,
            status=status,
            search=search
        )
        total = len(total_videos)
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        
        return PaginatedResponse(
            items=videos,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取收藏夹 {collection_id} 视频列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取视频列表失败")


@router.get("/{video_id}", response_model=VideoDetailResponse, summary="获取视频详情")
async def get_video_detail(video_id: int):
    """根据视频ID获取详细信息"""
    try:
        video = await video_dao.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail=f"视频 {video_id} 不存在")
        return video
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取视频 {video_id} 详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取视频详情失败")


@router.get("/bvid/{bvid}", response_model=List[VideoResponse], summary="根据BVID获取视频")
async def get_videos_by_bvid(bvid: str):
    """
    根据BVID获取视频信息
    
    一个视频可能存在于多个收藏夹中，所以返回列表
    """
    try:
        videos = await video_dao.get_video_by_bvid(bvid)
        if not videos:
            raise HTTPException(status_code=404, detail=f"视频 {bvid} 不存在")
        return videos
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"根据BVID {bvid} 获取视频失败: {e}")
        raise HTTPException(status_code=500, detail="获取视频失败")


@router.get("/{video_id}/stats", summary="获取视频统计信息")
async def get_video_stats(video_id: int, latest_only: bool = Query(True, description="是否只返回最新统计")):
    """获取视频的统计信息"""
    try:
        # 检查视频是否存在
        video = await video_dao.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail=f"视频 {video_id} 不存在")
        
        stats = await video_dao.get_video_stats(video_id, latest_only=latest_only)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取视频 {video_id} 统计信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取视频统计信息失败")


@router.post("/{video_id}/restore", response_model=SuccessResponse, summary="恢复已删除视频")
async def restore_video(video_id: int, collection_id: int):
    """恢复已删除的视频（标记为可用）"""
    try:
        # 检查视频是否存在
        video = await video_dao.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail=f"视频 {video_id} 不存在")
        
        # 检查收藏夹是否存在
        collection = await collection_dao.get_collection_by_id(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail=f"收藏夹 {collection_id} 不存在")
        
        # 恢复视频（将is_deleted设为False）
        await video_dao.add_to_collection(
            collection_id=collection_id,
            video_id=video_id,
            is_deleted=False
        )
        
        logger.info(f"已恢复视频: {video['title']} (ID: {video_id}) 在收藏夹 {collection['title']} 中")
        return SuccessResponse(
            message="视频恢复成功",
            data={
                "video_id": video_id,
                "video_title": video["title"],
                "collection_id": collection_id,
                "collection_title": collection["title"]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复视频 {video_id} 失败: {e}")
        raise HTTPException(status_code=500, detail="恢复视频失败")


@router.delete("/{video_id}", response_model=SuccessResponse, summary="删除视频")
async def delete_video(video_id: int, collection_id: int):
    """删除视频（标记为已删除）"""
    try:
        # 检查视频是否存在
        video = await video_dao.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail=f"视频 {video_id} 不存在")
        
        # 检查收藏夹是否存在
        collection = await collection_dao.get_collection_by_id(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail=f"收藏夹 {collection_id} 不存在")
        
        # 标记视频为已删除
        await video_dao.mark_as_deleted(collection_id, video_id, reason="手动删除")
        
        logger.info(f"已删除视频: {video['title']} (ID: {video_id}) 从收藏夹 {collection['title']} 中")
        return SuccessResponse(
            message="视频删除成功",
            data={
                "video_id": video_id,
                "video_title": video["title"],
                "collection_id": collection_id,
                "collection_title": collection["title"]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除视频 {video_id} 失败: {e}")
        raise HTTPException(status_code=500, detail="删除视频失败") 