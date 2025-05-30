"""
独立线程任务执行器
在单独的线程中执行长时间运行的任务，避免阻塞主线程
防止SQLite在多线程环境下的问题
"""
import asyncio
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import traceback

from ..models.task_models import BaseTask, TaskStatus, TaskType, TaskResult, VideoDownloadTask, SyncFavoritesTask
from ..dao.task_dao import task_dao
from ..dao.base import BaseDAO
from ..utils.logger import logger


class TaskExecutor:
    """独立线程任务执行器"""
    
    def __init__(self):
        self.is_running = False
        self.current_task: Optional[BaseTask] = None
        self.executor_thread: Optional[threading.Thread] = None
        self.should_stop = threading.Event()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 任务处理器注册表
        self.task_handlers: Dict[TaskType, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """注册任务处理器"""
        from .video_download_service import VideoDownloadService
        from .optimized_sync_service import optimized_sync_service
        
        # 注册下载任务处理器
        download_service = VideoDownloadService()
        self.task_handlers[TaskType.VIDEO_DOWNLOAD] = download_service.execute_download_task
        
        # 注册同步任务处理器  
        self.task_handlers[TaskType.SYNC_FAVORITES] = self._handle_sync_task
        
        # 注册批量下载任务处理器
        self.task_handlers[TaskType.BATCH_DOWNLOAD] = self._handle_batch_download_task
    
    def start(self):
        """启动任务执行器"""
        if self.is_running:
            logger.warning("任务执行器已在运行中")
            return
        
        self.should_stop.clear()
        self.is_running = True
        
        # 在新线程中启动任务循环
        self.executor_thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self.executor_thread.start()
        
        logger.info("任务执行器已启动")
    
    def stop(self):
        """停止任务执行器"""
        if not self.is_running:
            return
        
        logger.info("正在停止任务执行器...")
        self.should_stop.set()
        self.is_running = False
        
        # 等待线程结束
        if self.executor_thread and self.executor_thread.is_alive():
            self.executor_thread.join(timeout=10)
        
        logger.info("任务执行器已停止")
    
    def _run_in_thread(self):
        """在独立线程中运行任务循环"""
        # 创建新的事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            # 初始化数据库连接（表创建已移到init_db命令中）
            self.loop.run_until_complete(BaseDAO.initialize_database())
            
            # 运行任务循环
            self.loop.run_until_complete(self._task_loop())
            
        except Exception as e:
            logger.error(f"任务循环异常: {e}")
        finally:
            try:
                # 关闭数据库连接
                self.loop.run_until_complete(BaseDAO.close_database())
            except Exception as e:
                logger.error(f"关闭数据库连接失败: {e}")
            
            # 关闭事件循环
            self.loop.close()
    
    async def _task_loop(self):
        """任务执行主循环"""
        logger.info("任务执行循环已启动")
        
        while not self.should_stop.is_set():
            try:
                # 获取待执行的任务
                pending_tasks = await task_dao.get_tasks_by_status(TaskStatus.PENDING, limit=1)
                
                if pending_tasks:
                    task = pending_tasks[0]
                    await self._execute_task(task)
                else:
                    # 没有待执行任务，休眠一段时间
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"任务循环出错: {e}")
                await asyncio.sleep(5)
        
        logger.info("任务执行循环已退出")
    
    async def _execute_task(self, task: BaseTask):
        """执行单个任务"""
        self.current_task = task
        
        try:
            logger.info(f"开始执行任务: {task.task_id} - {task.title}")
            
            # 更新任务状态为运行中
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            await task_dao.save_task(task)
            
            # 获取任务处理器
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"未找到任务类型 {task.task_type} 的处理器")
            
            # 执行任务
            result = await handler(task)
            
            # 更新任务状态为完成
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            await task_dao.save_task(task)
            
            logger.info(f"任务执行完成: {task.task_id}")
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"任务执行失败: {task.task_id} - {e}\n{error_traceback}")
            
            # 更新任务状态为失败
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.result = TaskResult(
                success=False,
                data=None,
                error_message=str(e),
                error_code="EXECUTION_ERROR",
                output_files=[],
                statistics={}
            )
            
            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.started_at = None
                task.completed_at = None
                logger.info(f"任务将重试: {task.task_id} (第{task.retry_count}次重试)")
            
            await task_dao.save_task(task)
        
        finally:
            self.current_task = None
    
    async def _handle_sync_task(self, task: BaseTask) -> TaskResult:
        """处理同步收藏夹任务"""
        try:
            from .optimized_sync_service import optimized_sync_service
            
            collection_id = task.parameters.get("collection_id")
            force_covers = task.parameters.get("force_covers", False)
            
            # 设置进度回调
            async def progress_callback(current: int, total: int, message: str):
                task.progress.current = current
                task.progress.total = total
                task.progress.percentage = (current / total * 100) if total > 0 else 0
                task.progress.message = message
                await task_dao.save_task(task)
            
            # 执行同步
            if collection_id:
                stats = await optimized_sync_service.sync_single_collection(
                    collection_id, progress_callback=progress_callback
                )
            else:
                stats = await optimized_sync_service.sync_all_favorites(
                    progress_callback=progress_callback
                )
            
            return TaskResult(
                success=True,
                data=stats,
                error_message=None,
                error_code=None,
                output_files=[],
                statistics=stats
            )
            
        except Exception as e:
            logger.error(f"同步任务执行失败: {e}")
            return TaskResult(
                success=False,
                data=None,
                error_message=str(e),
                error_code="SYNC_ERROR",
                output_files=[],
                statistics={}
            )
    
    async def _handle_batch_download_task(self, task: BaseTask) -> TaskResult:
        """处理批量下载任务"""
        try:
            from .video_download_service import VideoDownloadService
            
            video_list = task.parameters.get("video_list", [])
            quality = task.parameters.get("quality", 80)
            
            download_service = VideoDownloadService()
            results = []
            successful_downloads = 0
            
            task.progress.total = len(video_list)
            
            for i, video_info in enumerate(video_list):
                try:
                    # 创建单个下载任务
                    download_task = VideoDownloadTask(
                        bvid=video_info["bvid"],
                        page=video_info.get("page", 0),
                        quality=quality
                    )
                    
                    # 执行下载
                    result = await download_service.execute_download_task(download_task)
                    results.append({
                        "bvid": video_info["bvid"],
                        "success": result.success,
                        "output_file": result.output_files[0] if result.output_files else None,
                        "error": result.error_message
                    })
                    
                    if result.success:
                        successful_downloads += 1
                    
                    # 更新进度
                    task.progress.current = i + 1
                    task.progress.percentage = (i + 1) / len(video_list) * 100
                    task.progress.message = f"已完成 {i + 1}/{len(video_list)} 个视频下载"
                    await task_dao.save_task(task)
                    
                except Exception as e:
                    logger.error(f"下载视频 {video_info['bvid']} 失败: {e}")
                    results.append({
                        "bvid": video_info["bvid"],
                        "success": False,
                        "output_file": None,
                        "error": str(e)
                    })
            
            return TaskResult(
                success=True,
                data={"downloads": results},
                error_message=None,
                error_code=None,
                output_files=[],
                statistics={
                    "total_videos": len(video_list),
                    "successful_downloads": successful_downloads,
                    "failed_downloads": len(video_list) - successful_downloads
                }
            )
            
        except Exception as e:
            logger.error(f"批量下载任务执行失败: {e}")
            return TaskResult(
                success=False,
                data=None,
                error_message=str(e),
                error_code="BATCH_DOWNLOAD_ERROR",
                output_files=[],
                statistics={}
            )
    
    def get_current_task(self) -> Optional[BaseTask]:
        """获取当前执行的任务"""
        return self.current_task
    
    def is_idle(self) -> bool:
        """检查执行器是否空闲"""
        return self.is_running and self.current_task is None


# 创建全局实例
task_executor = TaskExecutor() 