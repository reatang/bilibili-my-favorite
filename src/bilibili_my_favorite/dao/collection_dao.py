"""
收藏夹数据访问对象
提供收藏夹相关的数据库操作
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from .base import BaseDAO
from ..utils.logger import logger


class CollectionDAO(BaseDAO):
    """收藏夹数据访问对象"""
    
    async def get_all_collections(self) -> List[Dict[str, Any]]:
        """获取所有收藏夹"""
        query = """
        SELECT c.id, c.bilibili_fid, c.title, c.user_mid, c.description, 
               c.cover_url, c.media_count, c.last_synced, c.created_at, c.updated_at,
               u.name as user_name
        FROM collections c
        LEFT JOIN users u ON c.user_mid = u.mid
        ORDER BY c.title
        """
        rows = await self.execute_query(query)
        return self.rows_to_dicts(rows)
    
    async def get_collection_by_id(self, collection_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取收藏夹"""
        query = """
        SELECT c.id, c.bilibili_fid, c.title, c.user_mid, c.description, 
               c.cover_url, c.media_count, c.last_synced, c.created_at, c.updated_at,
               u.name as user_name
        FROM collections c
        LEFT JOIN users u ON c.user_mid = u.mid
        WHERE c.id = ?
        """
        row = await self.execute_one(query, (collection_id,))
        return self.row_to_dict(row)
    
    async def get_collection_by_bilibili_fid(self, bilibili_fid: str) -> Optional[Dict[str, Any]]:
        """根据B站收藏夹ID获取收藏夹"""
        query = """
        SELECT c.id, c.bilibili_fid, c.title, c.user_mid, c.description, 
               c.cover_url, c.media_count, c.last_synced, c.created_at, c.updated_at,
               u.name as user_name
        FROM collections c
        LEFT JOIN users u ON c.user_mid = u.mid
        WHERE c.bilibili_fid = ?
        """
        row = await self.execute_one(query, (bilibili_fid,))
        return self.row_to_dict(row)
    
    async def create_collection(self, bilibili_fid: str, title: str, user_mid: str,
                              description: str = None, cover_url: str = None) -> int:
        """创建新收藏夹"""
        now = datetime.now(timezone.utc)
        query = """
        INSERT INTO collections (bilibili_fid, title, user_mid, description, cover_url, 
                               created_at, updated_at, last_synced)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        return await self.execute_insert(
            query, (bilibili_fid, title, user_mid, description, cover_url, now, now, now)
        )
    
    async def update_collection(self, collection_id: int, title: str = None, 
                              description: str = None, cover_url: str = None,
                              media_count: int = None) -> int:
        """更新收藏夹信息"""
        now = datetime.now(timezone.utc)
        
        # 构建动态更新查询
        update_fields = []
        params = []
        
        if title is not None:
            update_fields.append("title = ?")
            params.append(title)
        if description is not None:
            update_fields.append("description = ?")
            params.append(description)
        if cover_url is not None:
            update_fields.append("cover_url = ?")
            params.append(cover_url)
        if media_count is not None:
            update_fields.append("media_count = ?")
            params.append(media_count)
        
        update_fields.append("updated_at = ?")
        params.append(now)
        params.append(collection_id)
        
        query = f"UPDATE collections SET {', '.join(update_fields)} WHERE id = ?"
        return await self.execute_update(query, tuple(params))
    
    async def update_sync_time(self, collection_id: int) -> int:
        """更新收藏夹同步时间"""
        now = datetime.now(timezone.utc)
        query = "UPDATE collections SET last_synced = ?, updated_at = ? WHERE id = ?"
        return await self.execute_update(query, (now, now, collection_id))
    
    async def delete_collection(self, collection_id: int) -> int:
        """删除收藏夹"""
        query = "DELETE FROM collections WHERE id = ?"
        return await self.execute_delete(query, (collection_id,))
    
    async def get_collection_stats(self, collection_id: int) -> Dict[str, Any]:
        """获取收藏夹统计信息"""
        query = """
        SELECT 
            COUNT(*) as total_videos,
            COUNT(CASE WHEN cv.is_deleted = 0 THEN 1 END) as available_videos,
            COUNT(CASE WHEN cv.is_deleted = 1 THEN 1 END) as deleted_videos,
            MAX(cv.last_seen) as last_video_seen
        FROM collection_videos cv
        WHERE cv.collection_id = ?
        """
        row = await self.execute_one(query, (collection_id,))
        return self.row_to_dict(row) or {
            'total_videos': 0, 'available_videos': 0, 
            'deleted_videos': 0, 'last_video_seen': None
        }


# 创建全局实例
collection_dao = CollectionDAO() 