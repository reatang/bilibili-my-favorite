"""
通用任务管理器
提供任务系统的对外接口，支持多种类型的长时间运行任务
"""
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable

from ..models.task_models import (
    BaseTask, TaskStatus, TaskType, TaskResult,
    VideoDownloadTask, SyncFavoritesTask, BatchDownloadTask
)
from ..models.types import (
    VideoDownloadItemDict, TaskStatusDict, TaskStatisticsDict,
    QueueInfoDict, SystemStatusDict, TaskListResponseDict,
    ActiveTasksResponseDict, CurrentTaskResponseDict
)
from ..dao.task_dao import task_dao
from .task_executor import task_executor
from ..utils.logger import logger


class TaskManager:
    """通用任务管理器"""
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self):
        """初始化任务管理器"""
        if self._initialized:
            return
        
        try:
            # 启动任务执行器（表创建已移到init_db命令中）
            task_executor.start()
            
            self._initialized = True
            logger.info("任务管理器初始化完成")
            
        except Exception as e:
            logger.error(f"任务管理器初始化失败: {e}")
            raise
    
    def shutdown(self):
        """关闭任务管理器"""
        if not self._initialized:
            return
        
        # 停止任务执行器
        task_executor.stop()
        self._initialized = False
        logger.info("任务管理器已关闭")
    
    # =============================================================================
    # 任务提交接口
    # =============================================================================
    
    async def submit_video_download(self, bvid: str, page: int = 0, quality: int = 80, 
                                  output_filename: Optional[str] = None, 
                                  ffmpeg_path: str = "ffmpeg",
                                  priority: int = 0) -> str:
        """提交视频下载任务"""
        task = VideoDownloadTask(
            bvid=bvid,
            page=page,
            quality=quality,
            output_filename=output_filename,
            ffmpeg_path=ffmpeg_path
        )
        task.priority = priority
        
        success = await task_dao.save_task(task)
        if success:
            logger.info(f"提交视频下载任务: {task.task_id} - {bvid}")
            return task.task_id
        else:
            raise RuntimeError("提交任务失败")
    
    async def submit_sync_favorites(self, collection_id: Optional[str] = None, 
                                  force_covers: bool = False,
                                  priority: int = 0) -> str:
        """提交同步收藏夹任务"""
        task = SyncFavoritesTask(
            collection_id=collection_id,
            force_covers=force_covers
        )
        task.priority = priority
        
        success = await task_dao.save_task(task)
        if success:
            logger.info(f"提交同步收藏夹任务: {task.task_id}")
            return task.task_id
        else:
            raise RuntimeError("提交任务失败")
    
    async def submit_batch_download(self, video_list: List[VideoDownloadItemDict], 
                                  quality: int = 80,
                                  priority: int = 0) -> str:
        """提交批量下载任务"""
        task = BatchDownloadTask(
            video_list=video_list,
            quality=quality
        )
        task.priority = priority
        
        success = await task_dao.save_task(task)
        if success:
            logger.info(f"提交批量下载任务: {task.task_id} - {len(video_list)} 个视频")
            return task.task_id
        else:
            raise RuntimeError("提交任务失败")
    
    async def submit_custom_task(self, task: BaseTask) -> str:
        """提交自定义任务"""
        success = await task_dao.save_task(task)
        if success:
            logger.info(f"提交自定义任务: {task.task_id} - {task.title}")
            return task.task_id
        else:
            raise RuntimeError("提交任务失败")
    
    # =============================================================================
    # 任务查询接口
    # =============================================================================
    
    async def get_task(self, task_id: str) -> Optional[BaseTask]:
        """获取任务详情"""
        return await task_dao.get_task_by_id(task_id)
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatusDict]:
        """获取任务状态（简化版本，适合API返回）"""
        task = await task_dao.get_task_by_id(task_id)
        if not task:
            return None
        
        return TaskStatusDict(
            task_id=task.task_id,
            task_type=task.task_type.value,
            title=task.title,
            status=task.status.value,
            progress={
                "current": task.progress.current,
                "total": task.progress.total,
                "percentage": task.progress.percentage,
                "message": task.progress.message
            },
            created_at=task.created_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            result={
                "success": task.result.success if task.result else False,
                "data": task.result.data if task.result else None,
                "error_message": task.result.error_message if task.result else None,
                "error_code": task.result.error_code if task.result else None,
                "output_files": task.result.output_files if task.result else [],
                "statistics": task.result.statistics if task.result else {}
            } if task.result else None
        )
    
    async def get_tasks_by_status(self, status: TaskStatus, limit: int = 50) -> List[TaskStatusDict]:
        """根据状态获取任务列表"""
        tasks = await task_dao.get_tasks_by_status(status, limit)
        result = []
        for task in tasks:
            task_status = await self.get_task_status(task.task_id)
            if task_status:
                result.append(task_status)
        return result
    
    async def get_tasks_by_type(self, task_type: TaskType, limit: int = 50) -> List[TaskStatusDict]:
        """根据类型获取任务列表"""
        tasks = await task_dao.get_tasks_by_type(task_type, limit)
        result = []
        for task in tasks:
            task_status = await self.get_task_status(task.task_id)
            if task_status:
                result.append(task_status)
        return result
    
    async def get_active_tasks(self) -> List[TaskStatusDict]:
        """获取活跃任务列表"""
        tasks = await task_dao.get_active_tasks()
        result = []
        for task in tasks:
            task_status = await self.get_task_status(task.task_id)
            if task_status:
                result.append(task_status)
        return result
    
    async def get_recent_tasks(self, limit: int = 50) -> List[TaskStatusDict]:
        """获取最近任务列表"""
        tasks = await task_dao.get_recent_tasks(limit)
        result = []
        for task in tasks:
            task_status = await self.get_task_status(task.task_id)
            if task_status:
                result.append(task_status)
        return result
    
    async def get_current_task(self) -> Optional[TaskStatusDict]:
        """获取当前正在执行的任务"""
        current_task = task_executor.get_current_task()
        if current_task:
            return await self.get_task_status(current_task.task_id)
        return None
    
    # =============================================================================
    # 任务控制接口
    # =============================================================================
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = await task_dao.get_task_by_id(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.PENDING, TaskStatus.PAUSED]:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            return await task_dao.save_task(task)
        
        return False
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务（仅对等待中的任务有效）"""
        task = await task_dao.get_task_by_id(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.PAUSED
            return await task_dao.save_task(task)
        
        return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        task = await task_dao.get_task_by_id(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.PENDING
            return await task_dao.save_task(task)
        
        return False
    
    async def retry_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        task = await task_dao.get_task_by_id(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.FAILED:
            task.status = TaskStatus.PENDING
            task.retry_count += 1
            task.started_at = None
            task.completed_at = None
            task.result = None
            return await task_dao.save_task(task)
        
        return False
    
    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        return await task_dao.delete_task(task_id)
    
    # =============================================================================
    # 系统管理接口
    # =============================================================================
    
    async def get_system_status(self) -> SystemStatusDict:
        """获取系统状态"""
        # 获取任务统计
        stats = await task_dao.get_task_statistics()
        
        # 获取执行器状态
        executor_status = {
            "is_running": task_executor.is_running,
            "is_idle": task_executor.is_idle(),
            "current_task": await self.get_current_task()
        }
        
        return SystemStatusDict(
            executor=executor_status,
            statistics=stats,
            timestamp=datetime.now().isoformat()
        )
    
    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """清理旧任务"""
        return await task_dao.cleanup_old_tasks(days)
    
    async def get_queue_info(self) -> QueueInfoDict:
        """获取任务队列信息"""
        pending_tasks = await task_dao.get_tasks_by_status(TaskStatus.PENDING)
        running_tasks = await task_dao.get_tasks_by_status(TaskStatus.RUNNING)
        
        # 按类型分组统计
        pending_by_type = {}
        for task in pending_tasks:
            task_type = task.task_type.value
            pending_by_type[task_type] = pending_by_type.get(task_type, 0) + 1
        
        return QueueInfoDict(
            pending_count=len(pending_tasks),
            running_count=len(running_tasks),
            pending_by_type=pending_by_type,
            estimated_wait_time=len(pending_tasks) * 60  # 简单估算，每个任务1分钟
        )
    
    # =============================================================================
    # 便捷方法
    # =============================================================================
    
    async def wait_for_task_completion(self, task_id: str, timeout: int = 3600) -> Optional[TaskResult]:
        """等待任务完成"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            task = await task_dao.get_task_by_id(task_id)
            if not task:
                return None
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return task.result
            
            await asyncio.sleep(2)
        
        return None
    
    async def is_task_running(self, task_id: str) -> bool:
        """检查任务是否正在运行"""
        task = await task_dao.get_task_by_id(task_id)
        return task is not None and task.status == TaskStatus.RUNNING


# 创建全局实例
task_manager = TaskManager() 