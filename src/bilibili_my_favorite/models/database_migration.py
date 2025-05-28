"""
数据库迁移脚本
将 is_deleted 和 deleted_at 字段从 collection_videos 表移动到 videos 表

字段说明：
- ogv_info: 存储官方影视作品信息的JSON字符串，如果此字段有值，说明该视频是B站官方影视作品
- season_info: 存储番剧/电视剧季度信息的JSON字符串
- first_cid: 视频的第一个分P的CID
"""
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from bilibili_my_favorite.core.config import config
from bilibili_my_favorite.utils.logger import logger


async def migrate_database():
    """执行数据库迁移"""
    logger.info("开始数据库迁移：将删除状态字段移动到videos表")
    
    db_path = config.DATABASE_PATH
    if not db_path.exists():
        logger.info("数据库文件不存在，无需迁移")
        return
    
    # 备份数据库
    backup_path = db_path.with_suffix('.backup')
    import shutil
    shutil.copy2(db_path, backup_path)
    logger.info(f"数据库已备份到: {backup_path}")
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        # 检查是否需要迁移
        cursor = await db.execute("PRAGMA table_info(videos)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'is_deleted' in column_names:
            logger.info("videos表已包含is_deleted字段，无需迁移")
            return
        
        logger.info("开始迁移数据库结构...")
        
        # 1. 为videos表添加新字段
        await db.execute("ALTER TABLE videos ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE")
        await db.execute("ALTER TABLE videos ADD COLUMN deleted_at TIMESTAMP")
        
        # 2. 迁移数据：将collection_videos中的删除状态合并到videos表
        # 如果一个视频在任何收藏夹中被标记为删除，则在videos表中标记为删除
        migration_query = """
        UPDATE videos 
        SET is_deleted = 1, 
            deleted_at = (
                SELECT MIN(cv.deleted_at) 
                FROM collection_videos cv 
                WHERE cv.video_id = videos.id AND cv.is_deleted = 1
            )
        WHERE id IN (
            SELECT DISTINCT cv.video_id 
            FROM collection_videos cv 
            WHERE cv.is_deleted = 1
        )
        """
        
        result = await db.execute(migration_query)
        migrated_count = result.rowcount
        logger.info(f"已迁移 {migrated_count} 个视频的删除状态")
        
        # 3. 创建新的collection_videos表（不包含删除状态字段）
        await db.execute("""
        CREATE TABLE collection_videos_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL,
            video_id INTEGER NOT NULL,
            fav_time INTEGER,
            first_seen TIMESTAMP NOT NULL,
            last_seen TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE,
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE,
            UNIQUE (collection_id, video_id)
        )
        """)
        
        # 4. 迁移collection_videos数据（排除删除状态字段）
        await db.execute("""
        INSERT INTO collection_videos_new 
        (id, collection_id, video_id, fav_time, first_seen, last_seen, created_at, updated_at)
        SELECT id, collection_id, video_id, fav_time, first_seen, last_seen, created_at, updated_at
        FROM collection_videos
        """)
        
        # 5. 删除旧表，重命名新表
        await db.execute("DROP TABLE collection_videos")
        await db.execute("ALTER TABLE collection_videos_new RENAME TO collection_videos")
        
        # 6. 重新创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_collection_videos_collection ON collection_videos (collection_id)",
            "CREATE INDEX IF NOT EXISTS idx_collection_videos_video ON collection_videos (video_id)",
            "CREATE INDEX IF NOT EXISTS idx_videos_deleted ON videos (is_deleted)"
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
        
        await db.commit()
        
        logger.info("数据库迁移完成")
        
        # 验证迁移结果
        cursor = await db.execute("SELECT COUNT(*) as count FROM videos WHERE is_deleted = 1")
        deleted_count = (await cursor.fetchone())["count"]
        
        cursor = await db.execute("SELECT COUNT(*) as count FROM collection_videos")
        cv_count = (await cursor.fetchone())["count"]
        
        logger.info(f"迁移验证：{deleted_count} 个已删除视频，{cv_count} 个收藏关系")


async def check_migration_needed() -> bool:
    """检查是否需要执行迁移"""
    db_path = config.DATABASE_PATH
    if not db_path.exists():
        return False
    
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("PRAGMA table_info(videos)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        return 'is_deleted' not in column_names


if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_database()) 