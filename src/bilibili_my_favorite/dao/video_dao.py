"""
视频数据访问对象
提供视频相关的数据库操作
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from .base import BaseDAO
from ..utils.logger import logger


class VideoDAO(BaseDAO):
    """视频数据访问对象"""
    
    async def get_videos_by_collection(self, collection_id: int, 
                                     status: str = "all", 
                                     search: str = None,
                                     limit: int = None, 
                                     offset: int = 0) -> List[Dict[str, Any]]:
        """根据收藏夹获取视频列表"""
        base_query = """
        SELECT v.id, v.bilibili_id, v.bvid, v.title, v.cover_url, v.local_cover_path,
               v.intro, v.duration, v.attr, v.ctime, v.pubtime,
               u.name as uploader_name, u.mid as uploader_mid, u.face_url as uploader_face,
               cv.fav_time, cv.is_deleted, cv.deleted_at, cv.first_seen, cv.last_seen
        FROM videos v
        JOIN collection_videos cv ON v.id = cv.video_id
        JOIN uploaders u ON v.uploader_mid = u.mid
        WHERE cv.collection_id = ?
        """
        params = [collection_id]
        
        # 添加状态过滤
        if status == "available":
            base_query += " AND cv.is_deleted = 0"
        elif status == "deleted":
            base_query += " AND cv.is_deleted = 1"
        
        # 添加搜索过滤
        if search:
            base_query += " AND (v.title LIKE ? OR u.name LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        # 添加排序
        base_query += " ORDER BY cv.last_seen DESC"
        
        # 添加分页
        if limit:
            base_query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        rows = await self.execute_query(base_query, tuple(params))
        return self.rows_to_dicts(rows)
    
    async def get_video_by_id(self, video_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取视频详情"""
        query = """
        SELECT v.id, v.bilibili_id, v.bvid, v.type, v.title, v.cover_url, v.local_cover_path,
               v.intro, v.page_count, v.duration, v.attr, v.ctime, v.pubtime,
               v.first_cid, v.season_info, v.ogv_info, v.link, v.media_list_link,
               v.created_at, v.updated_at,
               u.name as uploader_name, u.mid as uploader_mid, u.face_url as uploader_face,
               u.jump_link as uploader_jump_link
        FROM videos v
        JOIN uploaders u ON v.uploader_mid = u.mid
        WHERE v.id = ?
        """
        row = await self.execute_one(query, (video_id,))
        return self.row_to_dict(row)
    
    async def get_video_by_bvid(self, bvid: str) -> List[Dict[str, Any]]:
        """根据BVID获取视频（可能在多个收藏夹中）"""
        query = """
        SELECT v.id, v.bilibili_id, v.bvid, v.title, v.cover_url, v.local_cover_path,
               v.intro, v.duration, v.attr, v.ctime, v.pubtime,
               u.name as uploader_name, u.mid as uploader_mid, u.face_url as uploader_face,
               cv.collection_id, c.title as collection_title,
               cv.fav_time, cv.is_deleted, cv.deleted_at, cv.first_seen, cv.last_seen
        FROM videos v
        JOIN collection_videos cv ON v.id = cv.video_id
        JOIN collections c ON cv.collection_id = c.id
        JOIN uploaders u ON v.uploader_mid = u.mid
        WHERE v.bvid = ?
        ORDER BY cv.last_seen DESC
        """
        rows = await self.execute_query(query, (bvid,))
        return self.rows_to_dicts(rows)
    
    async def create_video(self, video_data: Dict[str, Any]) -> int:
        """创建新视频记录"""
        now = datetime.now(timezone.utc)
        query = """
        INSERT INTO videos (
            bilibili_id, bvid, type, title, cover_url, local_cover_path, intro, 
            page_count, duration, uploader_mid, attr, ctime, pubtime, 
            first_cid, season_info, ogv_info, link, media_list_link,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            video_data.get("bilibili_id"), video_data.get("bvid"), 
            video_data.get("type", 2), video_data.get("title"),
            video_data.get("cover_url"), video_data.get("local_cover_path"),
            video_data.get("intro", ""), video_data.get("page_count", 1),
            video_data.get("duration", 0), video_data.get("uploader_mid"),
            video_data.get("attr", 0), video_data.get("ctime"), video_data.get("pubtime"),
            video_data.get("first_cid"), video_data.get("season_info"),
            video_data.get("ogv_info"), video_data.get("link"), 
            video_data.get("media_list_link"), now, now
        )
        return await self.execute_insert(query, params)
    
    async def update_video(self, video_id: int, video_data: Dict[str, Any]) -> int:
        """更新视频信息"""
        now = datetime.now(timezone.utc)
        
        # 构建动态更新查询
        update_fields = []
        params = []
        
        updatable_fields = [
            "title", "cover_url", "local_cover_path", "page_count", 
            "duration", "attr", "ctime", "pubtime", "first_cid", "season_info", 
            "ogv_info", "link", "media_list_link"
        ]
        
        for field in updatable_fields:
            if field in video_data:
                update_fields.append(f"{field} = ?")
                params.append(video_data[field])
        
        if not update_fields:
            return 0
        
        update_fields.append("updated_at = ?")
        params.append(now)
        params.append(video_id)
        
        query = f"UPDATE videos SET {', '.join(update_fields)} WHERE id = ?"
        return await self.execute_update(query, tuple(params))
    
    async def add_to_collection(self, collection_id: int, video_id: int, 
                              fav_time: int = None, is_deleted: bool = False) -> int:
        """将视频添加到收藏夹"""
        now = datetime.now(timezone.utc)
        
        # 检查是否已存在
        existing = await self.execute_one(
            "SELECT id, is_deleted FROM collection_videos WHERE collection_id = ? AND video_id = ?",
            (collection_id, video_id)
        )
        
        if existing:
            # 更新现有记录
            deleted_at = now if is_deleted and not existing["is_deleted"] else None
            query = """
            UPDATE collection_videos SET 
                fav_time = ?, is_deleted = ?, deleted_at = ?, last_seen = ?, updated_at = ?
            WHERE collection_id = ? AND video_id = ?
            """
            await self.execute_update(
                query, (fav_time, is_deleted, deleted_at, now, now, collection_id, video_id)
            )
            return existing["id"]
        else:
            # 创建新记录
            deleted_at = now if is_deleted else None
            query = """
            INSERT INTO collection_videos (
                collection_id, video_id, fav_time, is_deleted, deleted_at,
                first_seen, last_seen, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            return await self.execute_insert(
                query, (collection_id, video_id, fav_time, is_deleted, deleted_at, 
                       now, now, now, now)
            )
    
    async def mark_as_deleted(self, collection_id: int, video_id: int, reason: str = None) -> int:
        """标记视频为已删除"""
        now = datetime.now(timezone.utc)
        query = """
        UPDATE collection_videos SET 
            is_deleted = 1, deleted_at = ?, updated_at = ?
        WHERE collection_id = ? AND video_id = ?
        """
        return await self.execute_update(query, (now, now, collection_id, video_id))
    
    async def get_video_stats(self, video_id: int, latest_only: bool = True) -> List[Dict[str, Any]]:
        """获取视频统计信息"""
        query = """
        SELECT video_id, collect_count, play_count, danmaku_count, reply_count,
               view_text, vt, play_switch, recorded_at
        FROM video_stats
        WHERE video_id = ?
        """
        if latest_only:
            query += " ORDER BY recorded_at DESC LIMIT 1"
        else:
            query += " ORDER BY recorded_at DESC"
        
        rows = await self.execute_query(query, (video_id,))
        return self.rows_to_dicts(rows)
    
    async def add_video_stats(self, video_id: int, stats_data: Dict[str, Any]) -> int:
        """添加视频统计信息"""
        now = datetime.now(timezone.utc)
        query = """
        INSERT INTO video_stats (
            video_id, collect_count, play_count, danmaku_count, reply_count,
            view_text, vt, play_switch, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            video_id, stats_data.get("collect", 0), stats_data.get("play", 0),
            stats_data.get("danmaku", 0), stats_data.get("reply", 0),
            stats_data.get("view_text_1", ""), stats_data.get("vt", 0),
            stats_data.get("play_switch", 0), now
        )
        return await self.execute_insert(query, params)


# 创建全局实例
video_dao = VideoDAO() 