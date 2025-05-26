"""
数据库模型定义
重新设计的表结构，更好地存储B站收藏夹数据
"""
import aiosqlite
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json
from contextlib import asynccontextmanager

from bilibili_my_favorite.core.config import config

@asynccontextmanager
async def get_db_connection():
    """建立异步SQLite数据库连接"""
    db = await aiosqlite.connect(config.DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def initialize_database():
    if config.DATABASE_PATH.exists():
        print(f"数据库文件已存在: {config.DATABASE_PATH}")
        return

    """初始化数据库并创建表结构"""
    async with get_db_connection() as db:
        # 用户表
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mid TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            face_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 收藏夹表
        await db.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bilibili_fid TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            user_mid TEXT NOT NULL,
            description TEXT,
            cover_url TEXT,
            media_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_synced TIMESTAMP,
            FOREIGN KEY (user_mid) REFERENCES users (mid) ON DELETE CASCADE
        );
        """)

        # UP主表
        await db.execute("""
        CREATE TABLE IF NOT EXISTS uploaders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mid TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            face_url TEXT,
            jump_link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 视频表
        await db.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bilibili_id TEXT NOT NULL,
            bvid TEXT NOT NULL,
            type INTEGER NOT NULL DEFAULT 2,
            title TEXT NOT NULL,
            cover_url TEXT,
            local_cover_path TEXT,
            intro TEXT,
            page_count INTEGER DEFAULT 1,
            duration INTEGER DEFAULT 0,
            uploader_mid TEXT NOT NULL,
            attr INTEGER DEFAULT 0,
            ctime INTEGER,
            pubtime INTEGER,
            first_cid TEXT,
            season_info TEXT,
            ogv_info TEXT,
            link TEXT,
            media_list_link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploader_mid) REFERENCES uploaders (mid) ON DELETE CASCADE,
            UNIQUE (bilibili_id, bvid)
        );
        """)

        # 收藏记录表（多对多关系）
        await db.execute("""
        CREATE TABLE IF NOT EXISTS collection_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL,
            video_id INTEGER NOT NULL,
            fav_time INTEGER,
            is_deleted BOOLEAN DEFAULT FALSE,
            deleted_at TIMESTAMP,
            first_seen TIMESTAMP NOT NULL,
            last_seen TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE,
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE,
            UNIQUE (collection_id, video_id)
        );
        """)

        # 视频统计表
        await db.execute("""
        CREATE TABLE IF NOT EXISTS video_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            collect_count INTEGER DEFAULT 0,
            play_count INTEGER DEFAULT 0,
            danmaku_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            view_text TEXT,
            vt INTEGER DEFAULT 0,
            play_switch INTEGER DEFAULT 0,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        );
        """)

        # 删除记录表
        await db.execute("""
        CREATE TABLE IF NOT EXISTS deletion_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL,
            video_bvid TEXT NOT NULL,
            video_title TEXT NOT NULL,
            uploader_name TEXT,
            deleted_at TIMESTAMP NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE
        );
        """)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_mid ON users (mid);",
            "CREATE INDEX IF NOT EXISTS idx_collections_fid ON collections (bilibili_fid);",
            "CREATE INDEX IF NOT EXISTS idx_collections_user ON collections (user_mid);",
            "CREATE INDEX IF NOT EXISTS idx_uploaders_mid ON uploaders (mid);",
            "CREATE INDEX IF NOT EXISTS idx_videos_bvid ON videos (bvid);",
            "CREATE INDEX IF NOT EXISTS idx_videos_bilibili_id ON videos (bilibili_id);",
            "CREATE INDEX IF NOT EXISTS idx_videos_uploader ON videos (uploader_mid);",
            "CREATE INDEX IF NOT EXISTS idx_collection_videos_collection ON collection_videos (collection_id);",
            "CREATE INDEX IF NOT EXISTS idx_collection_videos_video ON collection_videos (video_id);",
            "CREATE INDEX IF NOT EXISTS idx_collection_videos_deleted ON collection_videos (is_deleted);",
            "CREATE INDEX IF NOT EXISTS idx_video_stats_video ON video_stats (video_id);",
            "CREATE INDEX IF NOT EXISTS idx_deletion_logs_collection ON deletion_logs (collection_id);",
            "CREATE INDEX IF NOT EXISTS idx_deletion_logs_bvid ON deletion_logs (video_bvid);"
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)

        await db.commit()
    
    print(f"数据库初始化完成: {config.DATABASE_PATH}")


async def get_or_create_user(mid: str, name: str, face_url: str = None) -> int:
    """获取或创建用户记录"""
    async with await get_db_connection() as db:
        now = datetime.now(timezone.utc)
        cursor = await db.execute("SELECT id, name, face_url FROM users WHERE mid = ?", (mid,))
        row = await cursor.fetchone()
        
        if row:
            user_id = row["id"]
            # 更新用户信息
            if row["name"] != name or row["face_url"] != face_url:
                await db.execute(
                    "UPDATE users SET name = ?, face_url = ?, updated_at = ? WHERE id = ?",
                    (name, face_url, now, user_id)
                )
                await db.commit()
            return user_id
        else:
            cursor = await db.execute(
                "INSERT INTO users (mid, name, face_url, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (mid, name, face_url, now, now)
            )
            await db.commit()
            return cursor.lastrowid


async def get_or_create_uploader(mid: str, name: str, face_url: str = None, jump_link: str = None) -> int:
    """获取或创建UP主记录"""
    async with await get_db_connection() as db:
        now = datetime.now(timezone.utc)
        cursor = await db.execute("SELECT id, name, face_url, jump_link FROM uploaders WHERE mid = ?", (mid,))
        row = await cursor.fetchone()
        
        if row:
            uploader_id = row["id"]
            # 更新UP主信息
            if (row["name"] != name or row["face_url"] != face_url or row["jump_link"] != jump_link):
                await db.execute(
                    "UPDATE uploaders SET name = ?, face_url = ?, jump_link = ?, updated_at = ? WHERE id = ?",
                    (name, face_url, jump_link, now, uploader_id)
                )
                await db.commit()
            return uploader_id
        else:
            cursor = await db.execute(
                "INSERT INTO uploaders (mid, name, face_url, jump_link, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (mid, name, face_url, jump_link, now, now)
            )
            await db.commit()
            return cursor.lastrowid


async def get_or_create_collection(bilibili_fid: str, title: str, user_mid: str, 
                                 description: str = None, cover_url: str = None) -> int:
    """获取或创建收藏夹记录"""
    async with await get_db_connection() as db:
        now = datetime.now(timezone.utc)
        cursor = await db.execute("SELECT id, title, description, cover_url FROM collections WHERE bilibili_fid = ?", (bilibili_fid,))
        row = await cursor.fetchone()
        
        if row:
            collection_id = row["id"]
            # 更新收藏夹信息
            if (row["title"] != title or row["description"] != description or row["cover_url"] != cover_url):
                await db.execute(
                    "UPDATE collections SET title = ?, description = ?, cover_url = ?, updated_at = ?, last_synced = ? WHERE id = ?",
                    (title, description, cover_url, now, now, collection_id)
                )
                await db.commit()
            return collection_id
        else:
            cursor = await db.execute(
                """INSERT INTO collections (bilibili_fid, title, user_mid, description, cover_url, 
                   created_at, updated_at, last_synced) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (bilibili_fid, title, user_mid, description, cover_url, now, now, now)
            )
            await db.commit()
            return cursor.lastrowid


async def get_or_create_video(video_data: Dict[str, Any], uploader_id: int) -> int:
    """获取或创建视频记录"""
    async with await get_db_connection() as db:
        now = datetime.now(timezone.utc)
        bilibili_id = str(video_data["id"])
        bvid = video_data["bv_id"]
        
        cursor = await db.execute(
            "SELECT id FROM videos WHERE bilibili_id = ? AND bvid = ?", 
            (bilibili_id, bvid)
        )
        row = await cursor.fetchone()
        
        if row:
            video_id = row["id"]
            # 更新视频信息
            await db.execute("""
                UPDATE videos SET 
                    title = ?, cover_url = ?, intro = ?, page_count = ?, duration = ?,
                    attr = ?, ctime = ?, pubtime = ?, first_cid = ?, 
                    season_info = ?, ogv_info = ?, link = ?, media_list_link = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                video_data["title"], video_data["cover"], video_data.get("intro", ""),
                video_data.get("page", 1), video_data.get("duration", 0),
                video_data.get("attr", 0), video_data.get("ctime"), video_data.get("pubtime"),
                video_data.get("ugc", {}).get("first_cid") if video_data.get("ugc") else None,
                json.dumps(video_data.get("season")) if video_data.get("season") else None,
                json.dumps(video_data.get("ogv")) if video_data.get("ogv") else None,
                video_data.get("link"), video_data.get("media_list_link"),
                now, video_id
            ))
            await db.commit()
            return video_id
        else:
            cursor = await db.execute("""
                INSERT INTO videos (
                    bilibili_id, bvid, type, title, cover_url, intro, page_count, duration,
                    uploader_mid, attr, ctime, pubtime, first_cid, season_info, ogv_info,
                    link, media_list_link, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bilibili_id, bvid, video_data.get("type", 2), video_data["title"],
                video_data["cover"], video_data.get("intro", ""), video_data.get("page", 1),
                video_data.get("duration", 0), video_data["upper"]["mid"],
                video_data.get("attr", 0), video_data.get("ctime"), video_data.get("pubtime"),
                video_data.get("ugc", {}).get("first_cid") if video_data.get("ugc") else None,
                json.dumps(video_data.get("season")) if video_data.get("season") else None,
                json.dumps(video_data.get("ogv")) if video_data.get("ogv") else None,
                video_data.get("link"), video_data.get("media_list_link"),
                now, now
            ))
            await db.commit()
            return cursor.lastrowid


async def add_or_update_collection_video(collection_id: int, video_id: int, 
                                       fav_time: int, is_deleted: bool = False) -> int:
    """添加或更新收藏记录"""
    async with await get_db_connection() as db:
        now = datetime.now(timezone.utc)
        
        cursor = await db.execute(
            "SELECT id, is_deleted FROM collection_videos WHERE collection_id = ? AND video_id = ?",
            (collection_id, video_id)
        )
        row = await cursor.fetchone()
        
        if row:
            record_id = row["id"]
            deleted_at = now if is_deleted and not row["is_deleted"] else None
            await db.execute("""
                UPDATE collection_videos SET 
                    fav_time = ?, is_deleted = ?, deleted_at = ?, last_seen = ?, updated_at = ?
                WHERE id = ?
            """, (fav_time, is_deleted, deleted_at, now, now, record_id))
            await db.commit()
            return record_id
        else:
            deleted_at = now if is_deleted else None
            cursor = await db.execute("""
                INSERT INTO collection_videos (
                    collection_id, video_id, fav_time, is_deleted, deleted_at,
                    first_seen, last_seen, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (collection_id, video_id, fav_time, is_deleted, deleted_at, now, now, now, now))
            await db.commit()
            return cursor.lastrowid


async def add_video_stats(video_id: int, cnt_info: Dict[str, Any]) -> int:
    """添加视频统计信息"""
    async with await get_db_connection() as db:
        now = datetime.now(timezone.utc)
        cursor = await db.execute("""
            INSERT INTO video_stats (
                video_id, collect_count, play_count, danmaku_count, reply_count,
                view_text, vt, play_switch, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            video_id, cnt_info.get("collect", 0), cnt_info.get("play", 0),
            cnt_info.get("danmaku", 0), cnt_info.get("reply", 0),
            cnt_info.get("view_text_1", ""), cnt_info.get("vt", 0),
            cnt_info.get("play_switch", 0), now
        ))
        await db.commit()
        return cursor.lastrowid


async def log_deletion(collection_id: int, video_bvid: str, video_title: str, 
                      uploader_name: str, reason: str = None):
    """记录删除日志"""
    async with await get_db_connection() as db:
        now = datetime.now(timezone.utc)
        await db.execute("""
            INSERT INTO deletion_logs (
                collection_id, video_bvid, video_title, uploader_name, deleted_at, reason
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (collection_id, video_bvid, video_title, uploader_name, now, reason))
        await db.commit()


if __name__ == "__main__":
    import asyncio
    asyncio.run(initialize_database())
    print("数据库架构设置完成。您可以检查 bilibili_favorites.db") 