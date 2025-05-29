"""
收藏夹API路由
处理收藏夹相关的HTTP请求
"""
import math
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from ..dao.collection_dao import collection_dao
from ..dao.video_dao import video_dao
from ..services.optimized_sync_service import optimized_sync_service
from .models import (
    CollectionResponse, CollectionStatsResponse, SyncStatsResponse,
    SyncRequest, ErrorResponse, SuccessResponse, PaginatedResponse
)
from ..utils.logger import logger

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("/", response_model=List[CollectionResponse], summary="获取所有收藏夹")
async def get_all_collections():
    """获取所有收藏夹列表"""
    try:
        collections = await collection_dao.get_all_collections()
        return collections
    except Exception as e:
        logger.error(f"获取收藏夹列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取收藏夹列表失败")


@router.get("/{collection_id}/videos", response_model=PaginatedResponse, summary="获取收藏夹中的视频")
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


@router.get("/{collection_id}", response_model=CollectionResponse, summary="获取收藏夹详情")
async def get_collection(collection_id: int):
    """根据ID获取收藏夹详情"""
    try:
        collection = await collection_dao.get_collection_by_id(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail=f"收藏夹 {collection_id} 不存在")
        return collection
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取收藏夹 {collection_id} 失败: {e}")
        raise HTTPException(status_code=500, detail="获取收藏夹失败")


@router.get("/{collection_id}/stats", response_model=CollectionStatsResponse, summary="获取收藏夹统计信息")
async def get_collection_stats(collection_id: int):
    """获取收藏夹的统计信息"""
    try:
        # 检查收藏夹是否存在
        collection = await collection_dao.get_collection_by_id(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail=f"收藏夹 {collection_id} 不存在")
        
        stats = await collection_dao.get_collection_stats(collection_id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取收藏夹 {collection_id} 统计信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.post("/sync", response_model=SyncStatsResponse, summary="同步收藏夹")
async def sync_collections(sync_request: SyncRequest = None):
    """
    同步收藏夹数据
    
    - 如果指定collection_id，则只同步该收藏夹
    - 否则同步所有收藏夹
    """
    try:
        if sync_request and sync_request.collection_id:
            # 同步单个收藏夹
            logger.info(f"开始同步收藏夹: {sync_request.collection_id}")
            stats = await optimized_sync_service.sync_single_collection(sync_request.collection_id)
        else:
            # 同步所有收藏夹
            logger.info("开始同步所有收藏夹")
            stats = await optimized_sync_service.sync_all_favorites()
        
        return stats
    except Exception as e:
        logger.error(f"同步收藏夹失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/{collection_id}/sync", response_model=SyncStatsResponse, summary="同步指定收藏夹")
async def sync_single_collection(collection_id: str):
    """同步指定的收藏夹"""
    try:
        logger.info(f"开始同步收藏夹: {collection_id}")
        stats = await optimized_sync_service.sync_single_collection(collection_id)
        return stats
    except Exception as e:
        logger.error(f"同步收藏夹 {collection_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.delete("/{collection_id}", response_model=SuccessResponse, summary="删除收藏夹")
async def delete_collection(collection_id: int):
    """删除收藏夹（仅删除本地数据）"""
    try:
        # 检查收藏夹是否存在
        collection = await collection_dao.get_collection_by_id(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail=f"收藏夹 {collection_id} 不存在")
        
        # 删除收藏夹
        deleted_count = await collection_dao.delete_collection(collection_id)
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="收藏夹不存在或已被删除")
        
        logger.info(f"已删除收藏夹: {collection['title']} (ID: {collection_id})")
        return SuccessResponse(
            message="收藏夹删除成功",
            data={"collection_id": collection_id, "title": collection["title"]}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除收藏夹 {collection_id} 失败: {e}")
        raise HTTPException(status_code=500, detail="删除收藏夹失败") 