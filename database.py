import aiosqlite
import os
from datetime import datetime, timezone

DATABASE_NAME = "bilibili_favorites.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DATABASE_NAME)

async def get_db_connection():
    """Establishes an asynchronous connection to the SQLite database."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row # Access columns by name
    return db

async def initialize_database():
    """Initializes the database and creates tables if they don't exist."""
    async with await get_db_connection() as db:
        # Create collections table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bilibili_fid TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            last_synced TIMESTAMP
        );
        """)

        # Create videos table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bvid TEXT NOT NULL,
            collection_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            up_name TEXT,
            up_mid TEXT,
            cover_url TEXT,
            local_cover_path TEXT,
            first_seen TIMESTAMP NOT NULL,
            last_seen TIMESTAMP NOT NULL,
            is_deleted BOOLEAN DEFAULT FALSE,
            deleted_at TIMESTAMP,
            FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE,
            UNIQUE (bvid, collection_id) 
        );
        """)

        # Create an index on videos.bvid for faster lookups
        await db.execute("CREATE INDEX IF NOT EXISTS idx_videos_bvid ON videos (bvid);")
        # Create an index on videos.collection_id for faster lookups of videos in a collection
        await db.execute("CREATE INDEX IF NOT EXISTS idx_videos_collection_id ON videos (collection_id);")
        # Create an index on collections.bilibili_fid for faster lookups
        await db.execute("CREATE INDEX IF NOT EXISTS idx_collections_bilibili_fid ON collections (bilibili_fid);")

        await db.commit()
    print(f"Database initialized at {DB_PATH}")


async def get_or_create_collection(bilibili_fid: str, title: str) -> int:
    """Gets a collection by its bilibili_fid, creating it if it doesn't exist. Updates title if changed. Returns internal DB id."""
    async with await get_db_connection() as db:
        now = datetime.now(timezone.utc)
        cursor = await db.execute("SELECT id, title FROM collections WHERE bilibili_fid = ?", (bilibili_fid,))
        row = await cursor.fetchone()
        if row:
            collection_id = row["id"]
            if row["title"] != title:
                await db.execute("UPDATE collections SET title = ? WHERE id = ?", (title, collection_id))
            # Update last_synced for the collection
            await db.execute("UPDATE collections SET last_synced = ? WHERE id = ?", (now, collection_id))
            await db.commit()
            return collection_id
        else:
            cursor = await db.execute(
                "INSERT INTO collections (bilibili_fid, title, last_synced) VALUES (?, ?, ?)",
                (bilibili_fid, title, now)
            )
            await db.commit()
            return cursor.lastrowid

async def get_videos_by_collection_id(collection_id: int) -> dict[str, dict]:
    """Fetches all videos for a given collection_id, returned as a dict keyed by bvid."""
    async with await get_db_connection() as db:
        cursor = await db.execute("SELECT * FROM videos WHERE collection_id = ?", (collection_id,))
        rows = await cursor.fetchall()
        return {row["bvid"]: dict(row) for row in rows}

async def add_video(collection_id: int, video_data: dict, first_seen_time: datetime, local_cover_path: str = None):
    """Adds a new video to the database."""
    async with await get_db_connection() as db:
        is_deleted = video_data["title"] == "已失效视频"
        deleted_at = first_seen_time if is_deleted else None
        await db.execute("""
            INSERT INTO videos (
                bvid, collection_id, title, up_name, up_mid, cover_url, 
                local_cover_path, first_seen, last_seen, is_deleted, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            video_data["bv_id"], collection_id, video_data["title"], 
            video_data["upper"]["name"], video_data["upper"]["mid"], video_data["cover"],
            local_cover_path, first_seen_time, first_seen_time, is_deleted, deleted_at
        ))
        await db.commit()

async def update_video(video_id: int, video_data: dict, last_seen_time: datetime, db_video_data: dict, local_cover_path: str = None):
    """Updates an existing video's information."""
    async with await get_db_connection() as db:
        current_title = video_data["title"]
        current_is_deleted = current_title == "已失效视频"
        
        db_is_deleted = db_video_data["is_deleted"]
        
        new_is_deleted = current_is_deleted
        new_deleted_at = db_video_data["deleted_at"]

        if current_is_deleted and not db_is_deleted: # Video just became deleted
            new_deleted_at = last_seen_time
        elif not current_is_deleted and db_is_deleted: # Video became available again
            new_is_deleted = False
            new_deleted_at = None
        
        update_payload = {
            "title": current_title,
            "up_name": video_data["upper"]["name"],
            "up_mid": video_data["upper"]["mid"],
            "cover_url": video_data["cover"],
            "last_seen": last_seen_time,
            "is_deleted": new_is_deleted,
            "deleted_at": new_deleted_at
        }
        if local_cover_path is not None: # Only update if a new path is provided
             update_payload["local_cover_path"] = local_cover_path

        set_clause = ", ".join([f"{key} = :{key}" for key in update_payload.keys()])
        update_payload["id"] = video_id
        
        await db.execute(f"UPDATE videos SET {set_clause} WHERE id = :id", update_payload)
        await db.commit()

async def mark_video_as_deleted_by_bvid(bvid: str, collection_id: int, deleted_time: datetime):
    """Marks a video as deleted if it's no longer in API response."""
    async with await get_db_connection() as db:
        await db.execute("""
            UPDATE videos 
            SET is_deleted = TRUE, deleted_at = ?
            WHERE bvid = ? AND collection_id = ? AND is_deleted = FALSE
        """, (deleted_time, bvid, collection_id))
        await db.commit()

async def update_collection_sync_time(collection_id: int):
    """Updates the last_synced time for a collection."""
    async with await get_db_connection() as db:
        await db.execute("UPDATE collections SET last_synced = ? WHERE id = ?", (datetime.now(timezone.utc), collection_id))
        await db.commit()

if __name__ == "__main__":
    import asyncio
    asyncio.run(initialize_database())
    print("Database schema setup complete. You can inspect bilibili_favorites.db")
