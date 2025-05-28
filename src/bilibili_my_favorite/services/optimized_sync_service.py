"""
优化的同步服务
实现三步式同步流程以减少API调用
"""
import asyncio
import json
import random
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

from .sync_context import SyncContext
from .bilibili_service import bilibili_service
from ..dao.collection_dao import collection_dao
from ..dao.video_dao import video_dao
from ..models.database import (
    get_or_create_user, get_or_create_uploader, get_or_create_collection,
    get_or_create_video, add_or_update_collection_video, add_video_stats,
    log_deletion, initialize_database
)
from ..utils.downloader import cover_downloader
from ..utils.logger import logger
from ..core.config import config


class OptimizedSyncService:
    """优化的同步服务类"""
    
    def __init__(self):
        self.context: Optional[SyncContext] = None
    
    async def sync_all_favorites(self, uid: str = None, resume_task_id: str = None) -> Dict[str, Any]:
        """
        同步所有收藏夹（优化版本）
        
        Args:
            uid: 用户ID，默认使用配置中的用户ID
            resume_task_id: 要恢复的任务ID
            
        Returns:
            同步统计信息
        """
        try:
            # 步骤1: 初始化或恢复同步上下文
            if resume_task_id:
                self.context = await self._resume_sync_task(resume_task_id)
            else:
                self.context = await self._initialize_sync_task(uid)
            
            # 步骤2: 获取所有收藏夹数据（如果还没有完成）
            if self.context.status in ["initializing", "fetching"]:
                await self._fetch_all_collections_data()
                # 数据获取完成后，转换到处理阶段
                self.context.update_status("processing")
            
            # 步骤3: 处理数据入库和封面下载
            if self.context.status == "processing":
                await self._process_all_data()
            
            # 完成同步
            self.context.update_status("completed")
            stats = self.context.stats.copy()
            
            # 清理临时文件
            self.context.cleanup()
            
            logger.info(f"同步完成，统计信息: {stats}")
            return stats
            
        except Exception as e:
            if self.context:
                self.context.update_status("failed")
                self.context.stats["errors"].append(f"同步失败: {e}")
                stats = self.context.stats.copy()
                # 不清理临时文件，以便后续恢复
                return stats
            else:
                logger.error(f"同步过程中发生错误: {e}")
                return {
                    "collections_processed": 0,
                    "videos_added": 0,
                    "videos_updated": 0,
                    "videos_deleted": 0,
                    "covers_downloaded": 0,
                    "errors": [f"同步失败: {e}"],
                    "deleted_videos": []
                }
    
    async def sync_single_collection(self, bilibili_fid: str) -> Dict[str, Any]:
        """
        同步单个收藏夹（优化版本）
        
        Args:
            bilibili_fid: B站收藏夹ID
            
        Returns:
            同步统计信息
        """
        try:
            # 获取收藏夹信息
            collections = await bilibili_service.get_favorite_lists()
            collection_data = None
            
            for collection in collections:
                if str(collection["id"]) == str(bilibili_fid):
                    collection_data = collection
                    break
            
            if not collection_data:
                raise ValueError(f"未找到收藏夹 {bilibili_fid}")
            
            # 创建单个收藏夹的同步上下文
            self.context = SyncContext()
            self.context.collections_to_process = [collection_data]
            self.context.update_status("fetching")
            
            # 获取收藏夹数据
            await self._fetch_single_collection_data(collection_data)
            
            # 处理数据
            self.context.update_status("processing")
            await self._process_single_collection_data(collection_data)
            
            # 完成同步
            self.context.update_status("completed")
            stats = self.context.stats.copy()
            
            # 清理临时文件
            self.context.cleanup()
            
            logger.info(f"收藏夹 {bilibili_fid} 同步完成")
            return stats
            
        except Exception as e:
            if self.context:
                self.context.update_status("failed")
                self.context.stats["errors"].append(f"同步收藏夹 {bilibili_fid} 失败: {e}")
                return self.context.stats
            else:
                logger.error(f"同步收藏夹 {bilibili_fid} 失败: {e}")
                return {
                    "collections_processed": 0,
                    "videos_added": 0,
                    "videos_updated": 0,
                    "videos_deleted": 0,
                    "covers_downloaded": 0,
                    "errors": [f"同步收藏夹 {bilibili_fid} 失败: {e}"],
                    "deleted_videos": []
                }
    
    async def list_sync_tasks(self) -> List[Dict[str, Any]]:
        """列出所有同步任务"""
        lock_file = SyncContext.find_existing_lock_file()
        tasks = []
        
        try:
            context = SyncContext.load_from_lock_file(lock_file)
            tasks.append(context.get_progress_info())
        except Exception as e:
            logger.error(f"加载任务信息失败: {e}")
        
        return tasks
    
    async def resume_sync_task(self, task_id: str) -> Dict[str, Any]:
        """恢复指定的同步任务"""
        return await self.sync_all_favorites(resume_task_id=task_id)
    
    async def cancel_sync_task(self, task_id: str) -> bool:
        """取消指定的同步任务"""
        try:
            lock_file = SyncContext.find_existing_lock_file()
            if lock_file:
                context = SyncContext.load_from_lock_file(lock_file)
                context.update_status("cancelled")
                context.cleanup()
                logger.info(f"任务 {task_id} 已取消")
                return True
            
            logger.warning(f"未找到任务 {task_id}")
            return False
            
        except Exception as e:
            logger.error(f"取消任务 {task_id} 失败: {e}")
            return False
    
    async def _initialize_sync_task(self, uid: str = None) -> SyncContext:
        """初始化同步任务"""
        logger.info("初始化同步任务")
        
        # 确保数据库已初始化
        await initialize_database()
        
        # 确保必要目录存在
        config.ensure_actual_directories()
        
        # 创建同步上下文
        context = SyncContext()
        context.update_status("initializing")
        
        # 获取收藏夹列表
        collections = await bilibili_service.get_favorite_lists(uid)
        if not collections:
            raise ValueError("未获取到收藏夹列表")
        
        context.collections_to_process = collections
        context.save_lock_file()
        
        logger.info(f"初始化完成，共有 {len(collections)} 个收藏夹待处理")
        return context
    
    async def _resume_sync_task(self, task_id: str) -> SyncContext:
        """恢复同步任务"""
        logger.info(f"恢复同步任务: {task_id}")
        
        # 查找对应的锁文件
        lock_file = SyncContext.find_existing_lock_file()
        target_lock_file = None
        
        if lock_file:
            target_lock_file = lock_file
        
        if not target_lock_file:
            raise ValueError(f"未找到任务 {task_id} 的锁文件")
        
        # 加载同步上下文
        context = SyncContext.load_from_lock_file(target_lock_file)
        
        if not context.is_resumable():
            raise ValueError(f"任务 {task_id} 不可恢复，状态: {context.status}")
        
        logger.info(f"任务恢复成功，状态: {context.status}")
        return context
    
    async def _fetch_all_collections_data(self):
        """获取所有收藏夹的数据"""
        logger.info("开始获取所有收藏夹数据")
        self.context.update_status("fetching")
        
        # 如果有当前正在处理的收藏夹，从它开始
        if self.context.current_collection:
            # 继续处理当前收藏夹
            current_collection_id = str(self.context.current_collection.get('id'))
            await self._fetch_single_collection_data(
                self.context.current_collection, 
                start_page=self.context.current_page
            )
            # 数据拉取完成后，标记该收藏夹数据拉取完成
            self.context.mark_collection_data_fetched(current_collection_id)
        
        # 处理剩余的收藏夹
        # 使用副本遍历，避免在遍历过程中修改列表
        collections_copy = self.context.collections_to_process.copy()
        for collection_data in collections_copy:
            try:
                collection_id = str(collection_data.get('id'))
                self.context.set_current_collection(collection_data)
                await self._fetch_single_collection_data(collection_data)
                
                # 数据拉取完成后，标记该收藏夹数据拉取完成
                self.context.mark_collection_data_fetched(collection_id)
                
            except Exception as e:
                error_msg = f"获取收藏夹 {collection_data.get('title', 'Unknown')} 数据失败: {e}"
                logger.error(error_msg)
                self.context.mark_collection_failed(collection_data, str(e))
        
        logger.info("所有收藏夹数据获取完成")
    
    async def _fetch_single_collection_data(self, collection_data: Dict[str, Any], start_page: int = 1):
        """获取单个收藏夹的数据"""
        collection_id = str(collection_data["id"])
        title = collection_data["title"]
        
        logger.info(f"获取收藏夹数据: {title} (ID: {collection_id})")
        
        page = start_page
        has_more = True
        max_pages = config.MAX_PAGES_PER_COLLECTION
        
        while has_more and page <= max_pages:
            try:
                # 检查是否已有缓存数据
                cached_data = self.context.load_collection_page_data(collection_id, page)
                if cached_data is not None:
                    logger.debug(f"使用缓存数据: 收藏夹 {title} (ID: {collection_id}) 第 {page} 页")
                    page += 1
                    continue
                
                # 获取分页数据
                from bilibili_api import favorite_list
                
                result = await favorite_list.get_video_favorite_list_content(
                    media_id=int(collection_id), 
                    page=page, 
                    credential=bilibili_service.credential
                )
                
                if not result.get("medias"):
                    logger.info(f"收藏夹 {title} (ID: {collection_id}) 第 {page} 页无更多视频")
                    break
                
                videos = result["medias"]
                
                # 保存分页数据到文件
                self.context.save_collection_page_data(collection_id, page, videos)
                
                logger.info(f"收藏夹 {title} (ID: {collection_id}) 第 {page} 页获取到 {len(videos)} 个视频")
                
                has_more = result.get("has_more", False)
                page += 1
                
                # 更新当前页数
                self.context.current_page = page
                self.context.save_lock_file()
                
                # 添加请求延迟
                if has_more and page <= max_pages:
                    delay = random.uniform(config.REQUEST_DELAY, config.REQUEST_DELAY * 2) / 1000
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"获取收藏夹 {title} (ID: {collection_id}) 第 {page} 页失败: {e}")
                raise
        
        if page > max_pages:
            logger.warning(f"收藏夹 {title} (ID: {collection_id}) 超过最大页数限制 {max_pages}，停止获取")
        
        logger.info(f"收藏夹 {title} (ID: {collection_id}) 数据获取完成，共 {page - 1} 页")
    
    async def _process_all_data(self):
        """处理所有收藏夹的数据"""
        logger.info("开始处理所有收藏夹数据")
        
        # 获取所有有数据的收藏夹ID
        data_dir = self.context.data_dir
        if not data_dir.exists():
            logger.warning("数据目录不存在，没有数据需要处理")
            return
        
        collection_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
        
        # 处理每个有数据的收藏夹
        for collection_dir in collection_dirs:
            collection_id = collection_dir.name
            
            # 找到对应的收藏夹信息
            collection_data = None
            
            # 先从待处理列表中查找
            for collection in self.context.collections_to_process:
                if str(collection.get('id')) == collection_id:
                    collection_data = collection
                    break
            
            # 如果是当前正在处理的收藏夹
            if not collection_data and self.context.current_collection:
                if str(self.context.current_collection.get('id')) == collection_id:
                    collection_data = self.context.current_collection
            
            if not collection_data:
                logger.warning(f"未找到收藏夹 {collection_id} 的元数据，跳过处理")
                continue
            
            try:
                await self._process_single_collection_data(collection_data)
                
            except Exception as e:
                error_msg = f"处理收藏夹 {collection_data.get('title', 'Unknown')} 失败: {e}"
                error_traceback = traceback.format_exc()
                logger.error(f"{error_msg}\n错误栈:\n{error_traceback}")
                self.context.stats["errors"].append(error_msg)
        
        logger.info("所有收藏夹数据处理完成")
    
    async def _process_single_collection_data(self, collection_data: Dict[str, Any]):
        """处理单个收藏夹的数据"""
        collection_id = str(collection_data["id"])
        title = collection_data["title"]
        
        logger.info(f"处理收藏夹数据: {title} (ID: {collection_id})")
        
        # 创建或更新收藏夹记录
        user_mid = config.USER_DEDE_USER_ID
        db_collection_id = await get_or_create_collection(
            bilibili_fid=collection_id,
            title=title,
            user_mid=user_mid,
            description=collection_data.get("intro", ""),
            cover_url=collection_data.get("cover", "")
        )
        
        # 获取收藏夹的所有视频数据
        all_videos = self.context.get_collection_all_videos(collection_id)
        
        if not all_videos:
            logger.info(f"收藏夹 {title} 中没有视频")
            await collection_dao.update_sync_time(db_collection_id)
            self.context.mark_collection_completed(collection_id)
            return
        
        # 获取数据库中现有的视频
        existing_videos = await video_dao.get_videos_by_collection(db_collection_id)
        existing_bvids = {video["bvid"] for video in existing_videos}
        api_bvids = set()
        
        # 处理每个视频
        for video_data in all_videos:
            try:
                await self._process_video_data(video_data, db_collection_id)
                api_bvids.add(video_data["bv_id"])
            except Exception as e:
                error_msg = f"处理视频 {video_data.get('title', 'Unknown')} 失败: {e}"
                error_traceback = traceback.format_exc()
                logger.error(f"{error_msg}\n错误栈:\n{error_traceback}")
                self.context.stats["errors"].append(error_msg)
        
        # 标记已删除的视频
        deleted_bvids = existing_bvids - api_bvids
        for bvid in deleted_bvids:
            try:
                await self._mark_video_deleted(bvid, db_collection_id)
                self.context.stats["videos_deleted"] += 1
            except Exception as e:
                error_msg = f"标记视频 {bvid} 为已删除失败: {e}"
                error_traceback = traceback.format_exc()
                logger.error(f"{error_msg}\n错误栈:\n{error_traceback}")
                self.context.stats["errors"].append(error_msg)
        
        # 更新收藏夹同步时间
        await collection_dao.update_sync_time(db_collection_id)
        self.context.mark_collection_completed(collection_id)
        
        logger.info(f"收藏夹 {title} 处理完成")
    
    async def _process_video_data(self, video_data: Dict[str, Any], collection_id: int):
        """处理单个视频数据"""
        bvid = video_data["bv_id"]
        title = video_data["title"]
        
        # 检查视频是否已失效
        is_deleted = title == "已失效视频" or video_data.get("attr", 0) in [1, 9]
        
        # 创建或获取UP主
        uploader_data = video_data.get("upper", {})
        uploader_id = await get_or_create_uploader(
            mid=str(uploader_data.get("mid", "")),
            name=uploader_data.get("name", "Unknown"),
            face_url=uploader_data.get("face", ""),
            jump_link=uploader_data.get("jump_link", "")
        )
        
        # 准备视频数据
        ugc_data = video_data.get("ugc") or {}
        processed_video_data = {
            "bilibili_id": str(video_data["id"]),
            "bvid": bvid,
            "type": video_data.get("type", 2),
            "title": title,
            "cover_url": video_data.get("cover", ""),
            # "intro": video_data.get("intro", ""), # 只有创建时可以设置
            "page_count": video_data.get("page", 1),
            "duration": video_data.get("duration", 0),
            "uploader_mid": str(uploader_data.get("mid", "")),
            "attr": video_data.get("attr", 0),
            "ctime": video_data.get("ctime"),
            "pubtime": video_data.get("pubtime"),
            "first_cid": str(ugc_data.get("first_cid")) if ugc_data.get("first_cid") else None,
            "season_info": json.dumps(video_data.get("season"), ensure_ascii=False) if video_data.get("season") else None,
            "ogv_info": json.dumps(video_data.get("ogv"), ensure_ascii=False) if video_data.get("ogv") else None,
            "link": video_data.get("link"),
            "media_list_link": video_data.get("media_list_link")
        }
        
        # 检查视频是否已存在（不限制收藏夹ID，因为视频表有全局唯一约束）
        existing_video = await video_dao.get_video_by_bvid(bvid)
        
        if existing_video:
            # 更新现有视频信息
            video_id = existing_video["id"]
            
            # 检查视频状态变化
            current_deleted = existing_video.get("is_deleted", False)
            
            if not current_deleted and is_deleted:
                # 视频变为不可用
                processed_video_data["is_deleted"] = True
                processed_video_data["deleted_at"] = datetime.now(timezone.utc)
                if "已失效视频" not in existing_video["title"]:
                    processed_video_data["title"] = f"{existing_video['title']} (已失效视频)"
                logger.info(f"视频 '{existing_video['title']}' (BVID: {bvid}) 变为不可用")
            elif current_deleted and not is_deleted:
                # 视频恢复可用
                processed_video_data["is_deleted"] = False
                processed_video_data["deleted_at"] = None
                # 恢复视频标题（移除失效标记）
                if "已失效视频" in existing_video["title"]:
                    original_title = existing_video["title"].replace(" (已失效视频)", "")
                    processed_video_data["title"] = title if title != "已失效视频" else original_title
                logger.info(f"视频 '{title}' (BVID: {bvid}) 恢复可用")
            else:
                # 状态没有变化，但可能需要更新其他信息
                processed_video_data["is_deleted"] = is_deleted
                if is_deleted:
                    processed_video_data["deleted_at"] = existing_video.get("deleted_at")

            await video_dao.update_video(video_id, processed_video_data)
            self.context.stats["videos_updated"] += 1
        else:
            # 创建新视频记录
            processed_video_data["intro"] = video_data.get("intro", "")
            processed_video_data["is_deleted"] = is_deleted
            if is_deleted:
                processed_video_data["deleted_at"] = datetime.now(timezone.utc)
            
            try:
                video_id = await video_dao.create_video(processed_video_data)
                if is_deleted:
                    logger.info(f"新视频 '{title}' (BVID: {bvid}) 为不可用状态")
                self.context.stats["videos_added"] += 1
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    # 并发情况下可能出现重复插入，重新查询
                    logger.warning(f"视频 {bvid} 插入时发生唯一约束冲突，重新查询")
                    existing_video = await video_dao.get_video_by_bvid(bvid)
                    if existing_video:
                        video_id = existing_video["id"]
                        await video_dao.update_video(video_id, processed_video_data)
                        self.context.stats["videos_updated"] += 1
                    else:
                        raise
                else:
                    raise
        
        # 更新收藏关系
        await video_dao.add_to_collection(
            collection_id=collection_id,
            video_id=video_id,
            fav_time=video_data.get("fav_time")
        )
        
        # 添加统计信息
        if video_data.get("cnt_info"):
            await video_dao.add_video_stats(video_id, video_data["cnt_info"])
        
        # 下载封面（仅对有效视频）
        if not is_deleted and video_data.get("cover"):
            await self._download_cover_if_needed(bvid, video_data["cover"], video_id)
    
    async def _download_cover_if_needed(self, bvid: str, cover_url: str, video_id: int):
        """根据需要下载封面"""
        try:
            # 检查是否需要下载封面
            video = await video_dao.get_video_by_id(video_id)
            if video and video.get("local_cover_path"):
                # 已有本地封面，跳过
                return
            
            # 下载封面
            local_path = await cover_downloader.download_cover(bvid, cover_url)
            if local_path:
                # 更新视频记录中的本地封面路径
                await video_dao.update_video(video_id, {"local_cover_path": local_path})
                self.context.stats["covers_downloaded"] += 1
                
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"下载封面失败: BVID {bvid}, 错误: {e}\n错误栈:\n{error_traceback}")
    
    async def _mark_video_deleted(self, bvid: str, collection_id: int):
        """标记视频为已删除"""
        video = await video_dao.get_video_by_bvid(bvid)
        if not video:
            logger.warning(f"未找到要删除的视频: {bvid}")
            return
            
        # 获取收藏夹信息用于记录
        collection = await collection_dao.get_collection_by_id(collection_id)
        collection_title = collection["title"] if collection else f"收藏夹ID:{collection_id}"
        
        # 记录被删除的视频信息
        deleted_video_info = {
            "bvid": bvid,
            "title": video["title"],
            "uploader_name": video.get("uploader_name", "Unknown"),
            "collection_title": collection_title,
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }
        self.context.stats["deleted_videos"].append(deleted_video_info)
        
        # 标记视频为已删除
        await video_dao.mark_as_deleted(video["id"])
        
        # 从收藏夹中移除视频
        await video_dao.remove_from_collection(collection_id, video["id"])
        
        # 记录删除日志
        await log_deletion(
            collection_id=collection_id,
            video_bvid=bvid,
            video_title=video["title"],
            uploader_name=video.get("uploader_name", "Unknown"),
            reason="从B站收藏夹中移除"
        )
        
        logger.info(f"视频 '{video['title']}' (BVID: {bvid}) 已从收藏夹 '{collection_title}' 中删除")


# 创建全局服务实例
optimized_sync_service = OptimizedSyncService() 