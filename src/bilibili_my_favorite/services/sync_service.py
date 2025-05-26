"""
同步服务
处理收藏夹同步的核心业务逻辑
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional
from ..dao.collection_dao import collection_dao
from ..dao.video_dao import video_dao
from ..models.database import (
    get_or_create_user, get_or_create_uploader, get_or_create_collection,
    get_or_create_video, add_or_update_collection_video, add_video_stats,
    log_deletion, initialize_database
)
from ..services.bilibili_service import bilibili_service
from ..utils.downloader import cover_downloader
from ..utils.logger import logger
from ..core.config import config


class SyncService:
    """同步服务类"""
    
    def __init__(self):
        self.sync_stats = {
            "collections_processed": 0,
            "videos_added": 0,
            "videos_updated": 0,
            "videos_deleted": 0,
            "covers_downloaded": 0,
            "errors": []
        }
    
    async def initialize_database(self):
        """初始化数据库"""
        await initialize_database()
        logger.info("数据库初始化完成")
    
    async def sync_all_favorites(self, uid: str = None) -> Dict[str, Any]:
        """
        同步所有收藏夹
        
        Args:
            uid: 用户ID，默认使用配置中的用户ID
            
        Returns:
            同步统计信息
        """
        logger.info("开始同步所有收藏夹")
        self._reset_stats()
        
        try:
            # 确保数据库已初始化
            await self.initialize_database()
            
            # 确保必要目录存在
            config.ensure_actual_directories()
            
            # 获取收藏夹列表
            collections = await bilibili_service.get_favorite_lists(uid)
            if not collections:
                logger.warning("未获取到收藏夹列表")
                return self.sync_stats
            
            # 处理每个收藏夹
            for collection_data in collections:
                try:
                    await self._sync_single_collection(collection_data)
                    self.sync_stats["collections_processed"] += 1
                except Exception as e:
                    error_msg = f"同步收藏夹 {collection_data.get('title', 'Unknown')} 失败: {e}"
                    logger.error(error_msg)
                    self.sync_stats["errors"].append(error_msg)
            
            logger.info(f"同步完成，统计信息: {self.sync_stats}")
            return self.sync_stats
            
        except Exception as e:
            error_msg = f"同步过程中发生错误: {e}"
            logger.error(error_msg)
            self.sync_stats["errors"].append(error_msg)
            return self.sync_stats
    
    async def sync_single_collection(self, bilibili_fid: str) -> Dict[str, Any]:
        """
        同步单个收藏夹
        
        Args:
            bilibili_fid: B站收藏夹ID
            
        Returns:
            同步统计信息
        """
        logger.info(f"开始同步收藏夹 {bilibili_fid}")
        self._reset_stats()
        
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
            
            await self._sync_single_collection(collection_data)
            self.sync_stats["collections_processed"] = 1
            
            logger.info(f"收藏夹 {bilibili_fid} 同步完成")
            return self.sync_stats
            
        except Exception as e:
            error_msg = f"同步收藏夹 {bilibili_fid} 失败: {e}"
            logger.error(error_msg)
            self.sync_stats["errors"].append(error_msg)
            return self.sync_stats
    
    async def _sync_single_collection(self, collection_data: Dict[str, Any]):
        """同步单个收藏夹的内部实现"""
        bilibili_fid = str(collection_data["id"])
        title = collection_data["title"]
        
        logger.info(f"处理收藏夹: {title} (FID: {bilibili_fid})")
        
        # 创建或更新收藏夹记录
        user_mid = config.USER_DEDE_USER_ID
        collection_id = await get_or_create_collection(
            bilibili_fid=bilibili_fid,
            title=title,
            user_mid=user_mid,
            description=collection_data.get("intro", ""),
            cover_url=collection_data.get("cover", "")
        )
        
        # 获取收藏夹中的视频
        videos = await bilibili_service.get_favorite_videos(int(bilibili_fid))
        if not videos:
            logger.info(f"收藏夹 {title} 中没有视频")
            await collection_dao.update_sync_time(collection_id)
            return
        
        # 获取数据库中现有的视频
        existing_videos = await video_dao.get_videos_by_collection(collection_id)
        existing_bvids = {video["bvid"] for video in existing_videos}
        api_bvids = set()
        
        # 处理每个视频
        for video_data in videos:
            try:
                await self._process_video(video_data, collection_id)
                api_bvids.add(video_data["bv_id"])
            except Exception as e:
                error_msg = f"处理视频 {video_data.get('title', 'Unknown')} 失败: {e}"
                logger.error(error_msg)
                self.sync_stats["errors"].append(error_msg)
        
        # 标记已删除的视频
        deleted_bvids = existing_bvids - api_bvids
        for bvid in deleted_bvids:
            try:
                await self._mark_video_deleted(bvid, collection_id)
                self.sync_stats["videos_deleted"] += 1
            except Exception as e:
                error_msg = f"标记视频 {bvid} 为已删除失败: {e}"
                logger.error(error_msg)
                self.sync_stats["errors"].append(error_msg)
        
        # 更新收藏夹同步时间
        await collection_dao.update_sync_time(collection_id)
        logger.info(f"收藏夹 {title} 处理完成")
    
    async def _process_video(self, video_data: Dict[str, Any], collection_id: int):
        """处理单个视频"""
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
        processed_video_data = {
            "bilibili_id": str(video_data["id"]),
            "bvid": bvid,
            "type": video_data.get("type", 2),
            "title": title,
            "cover_url": video_data.get("cover", ""),
            "intro": video_data.get("intro", ""),
            "page_count": video_data.get("page", 1),
            "duration": video_data.get("duration", 0),
            "uploader_mid": str(uploader_data.get("mid", "")),
            "attr": video_data.get("attr", 0),
            "ctime": video_data.get("ctime"),
            "pubtime": video_data.get("pubtime"),
            "first_cid": video_data.get("ugc", {}).get("first_cid") if video_data.get("ugc") else None,
            "season_info": json.dumps(video_data.get("season")) if video_data.get("season") else None,
            "ogv_info": json.dumps(video_data.get("ogv")) if video_data.get("ogv") else None,
            "link": video_data.get("link"),
            "media_list_link": video_data.get("media_list_link")
        }
        
        # 检查视频是否已存在
        existing_videos = await video_dao.get_video_by_bvid(bvid)
        existing_video = None
        for video in existing_videos:
            if video["collection_id"] == collection_id:
                existing_video = video
                break
        
        if existing_video:
            # 更新现有视频
            video_id = existing_video["id"]
            await video_dao.update_video(video_id, processed_video_data)
            
            # 检查状态变化
            if existing_video["title"] != "已失效视频" and is_deleted:
                logger.info(f"视频 '{existing_video['title']}' (BVID: {bvid}) 变为不可用")
            elif existing_video["is_deleted"] and not is_deleted:
                logger.info(f"视频 '{title}' (BVID: {bvid}) 恢复可用")
            
            self.sync_stats["videos_updated"] += 1
        else:
            # 创建新视频
            video_id = await video_dao.create_video(processed_video_data)
            
            if is_deleted:
                logger.info(f"新视频 '{title}' (BVID: {bvid}) 为不可用状态")
            
            self.sync_stats["videos_added"] += 1
        
        # 更新收藏关系
        await video_dao.add_to_collection(
            collection_id=collection_id,
            video_id=video_id,
            fav_time=video_data.get("fav_time"),
            is_deleted=is_deleted
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
                self.sync_stats["covers_downloaded"] += 1
                
        except Exception as e:
            logger.error(f"下载封面失败: BVID {bvid}, 错误: {e}")
    
    async def _mark_video_deleted(self, bvid: str, collection_id: int):
        """标记视频为已删除"""
        videos = await video_dao.get_video_by_bvid(bvid)
        for video in videos:
            if video["collection_id"] == collection_id:
                await video_dao.mark_as_deleted(collection_id, video["id"])
                
                # 记录删除日志
                await log_deletion(
                    collection_id=collection_id,
                    video_bvid=bvid,
                    video_title=video["title"],
                    uploader_name=video["uploader_name"],
                    reason="从B站收藏夹中移除"
                )
                
                logger.info(f"视频 '{video['title']}' (BVID: {bvid}) 已从收藏夹中删除")
                break
    
    def _reset_stats(self):
        """重置统计信息"""
        self.sync_stats = {
            "collections_processed": 0,
            "videos_added": 0,
            "videos_updated": 0,
            "videos_deleted": 0,
            "covers_downloaded": 0,
            "errors": []
        }


# # 创建全局服务实例
sync_service = SyncService() 