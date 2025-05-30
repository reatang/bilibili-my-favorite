"""
任务管理API
为Web端提供任务相关的HTTP接口
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..services.task_manager import task_manager
from ..models.task_models import TaskStatus, TaskType
from ..models.types import (
    VideoDownloadItemDict, TaskStatusDict, TaskListResponseDict,
    ActiveTasksResponseDict, CurrentTaskResponseDict, SystemStatusDict,
    QueueInfoDict
)
from ..utils.logger import logger

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# =============================================================================
# 请求/响应模型
# =============================================================================

class VideoDownloadRequest(BaseModel):
    """视频下载请求"""
    bvid: str
    page: int = 0
    quality: int = 80
    output_filename: Optional[str] = None
    ffmpeg_path: str = "ffmpeg"
    priority: int = 0


class SyncFavoritesRequest(BaseModel):
    """同步收藏夹请求"""
    collection_id: Optional[str] = None
    force_covers: bool = False
    priority: int = 0


class BatchDownloadRequest(BaseModel):
    """批量下载请求"""
    video_list: List[VideoDownloadItemDict]
    quality: int = 80
    priority: int = 0


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    task_type: str
    title: str
    status: str
    progress: Dict[str, Any]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[Dict[str, Any]]


class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    executor: Dict[str, Any]
    statistics: Dict[str, Any]
    timestamp: str


# =============================================================================
# 任务提交接口
# =============================================================================

@router.post("/download", response_model=TaskResponse)
async def submit_download_task(request: VideoDownloadRequest):
    """提交视频下载任务"""
    try:
        task_id = await task_manager.submit_video_download(
            bvid=request.bvid,
            page=request.page,
            quality=request.quality,
            output_filename=request.output_filename,
            ffmpeg_path=request.ffmpeg_path,
            priority=request.priority
        )
        
        logger.info(f"Web端提交下载任务: {task_id} - {request.bvid}")
        
        return TaskResponse(
            task_id=task_id,
            message=f"下载任务已提交: {request.bvid} P{request.page + 1}"
        )
        
    except Exception as e:
        logger.error(f"提交下载任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=TaskResponse)
async def submit_sync_task(request: SyncFavoritesRequest):
    """提交同步收藏夹任务"""
    try:
        task_id = await task_manager.submit_sync_favorites(
            collection_id=request.collection_id,
            force_covers=request.force_covers,
            priority=request.priority
        )
        
        logger.info(f"Web端提交同步任务: {task_id}")
        
        return TaskResponse(
            task_id=task_id,
            message="同步任务已提交" if not request.collection_id else f"同步任务已提交: {request.collection_id}"
        )
        
    except Exception as e:
        logger.error(f"提交同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-download", response_model=TaskResponse)
async def submit_batch_download_task(request: BatchDownloadRequest):
    """提交批量下载任务"""
    try:
        if not request.video_list:
            raise HTTPException(status_code=400, detail="视频列表不能为空")
        
        task_id = await task_manager.submit_batch_download(
            video_list=request.video_list,
            quality=request.quality,
            priority=request.priority
        )
        
        logger.info(f"Web端提交批量下载任务: {task_id} - {len(request.video_list)} 个视频")
        
        return TaskResponse(
            task_id=task_id,
            message=f"批量下载任务已提交: {len(request.video_list)} 个视频"
        )
        
    except Exception as e:
        logger.error(f"提交批量下载任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 任务查询接口
# =============================================================================

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        status = await task_manager.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return TaskStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def get_task_list(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 50
) -> TaskListResponseDict:
    """获取任务列表"""
    try:
        if status:
            # 按状态查询
            try:
                task_status = TaskStatus(status)
                tasks = await task_manager.get_tasks_by_status(task_status, limit)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的任务状态")
        elif task_type:
            # 按类型查询
            try:
                task_type_enum = TaskType(task_type)
                tasks = await task_manager.get_tasks_by_type(task_type_enum, limit)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的任务类型")
        else:
            # 获取最近任务
            tasks = await task_manager.get_recent_tasks(limit)
        
        return TaskListResponseDict(
            tasks=tasks,
            total=len(tasks)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_tasks() -> ActiveTasksResponseDict:
    """获取活跃任务"""
    try:
        tasks = await task_manager.get_active_tasks()
        return ActiveTasksResponseDict(
            tasks=tasks,
            total=len(tasks)
        )
        
    except Exception as e:
        logger.error(f"获取活跃任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_task() -> CurrentTaskResponseDict:
    """获取当前执行的任务"""
    try:
        current_task = await task_manager.get_current_task()
        return CurrentTaskResponseDict(
            current_task=current_task
        )
        
    except Exception as e:
        logger.error(f"获取当前任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 任务控制接口
# =============================================================================

@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        success = await task_manager.cancel_task(task_id)
        if success:
            return {"message": "任务已取消"}
        else:
            raise HTTPException(status_code=400, detail="无法取消该任务")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause/{task_id}")
async def pause_task(task_id: str):
    """暂停任务"""
    try:
        success = await task_manager.pause_task(task_id)
        if success:
            return {"message": "任务已暂停"}
        else:
            raise HTTPException(status_code=400, detail="无法暂停该任务")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"暂停任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume/{task_id}")
async def resume_task(task_id: str):
    """恢复任务"""
    try:
        success = await task_manager.resume_task(task_id)
        if success:
            return {"message": "任务已恢复"}
        else:
            raise HTTPException(status_code=400, detail="无法恢复该任务")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry/{task_id}")
async def retry_task(task_id: str):
    """重试任务"""
    try:
        success = await task_manager.retry_task(task_id)
        if success:
            return {"message": "任务已重新提交"}
        else:
            raise HTTPException(status_code=400, detail="无法重试该任务")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重试任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    try:
        success = await task_manager.delete_task(task_id)
        if success:
            return {"message": "任务已删除"}
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 系统管理接口
# =============================================================================

@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    """获取系统状态"""
    try:
        status = await task_manager.get_system_status()
        return SystemStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/queue")
async def get_queue_info() -> QueueInfoDict:
    """获取任务队列信息"""
    try:
        queue_info = await task_manager.get_queue_info()
        return queue_info
        
    except Exception as e:
        logger.error(f"获取队列信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/cleanup")
async def cleanup_old_tasks(days: int = 30):
    """清理旧任务"""
    try:
        count = await task_manager.cleanup_old_tasks(days)
        return {"message": f"清理了 {count} 个旧任务"}
        
    except Exception as e:
        logger.error(f"清理旧任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WebSocket接口（用于实时进度更新）
# =============================================================================

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json

@router.websocket("/ws/{task_id}")
async def websocket_task_progress(websocket: WebSocket, task_id: str):
    """WebSocket接口，实时推送任务进度"""
    await websocket.accept()
    
    try:
        while True:
            # 获取任务状态
            status = await task_manager.get_task_status(task_id)
            
            if not status:
                await websocket.send_text(json.dumps({
                    "error": "任务不存在"
                }))
                break
            
            # 发送状态更新
            await websocket.send_text(json.dumps({
                "task_id": task_id,
                "status": status["status"],
                "progress": status["progress"],
                "result": status["result"]
            }))
            
            # 如果任务已完成，停止推送
            if status["status"] in ["completed", "failed", "cancelled"]:
                break
            
            # 等待2秒后再次查询
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {task_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        await websocket.send_text(json.dumps({
            "error": str(e)
        }))


@router.websocket("/ws/system")
async def websocket_system_status(websocket: WebSocket):
    """WebSocket接口，实时推送系统状态"""
    await websocket.accept()
    
    try:
        while True:
            # 获取系统状态
            status = await task_manager.get_system_status()
            
            # 发送状态更新
            await websocket.send_text(json.dumps(status))
            
            # 等待5秒后再次查询
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        logger.info("系统状态WebSocket连接断开")
    except Exception as e:
        logger.error(f"系统状态WebSocket错误: {e}")
        await websocket.send_text(json.dumps({
            "error": str(e)
        })) 