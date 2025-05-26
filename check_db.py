import asyncio
import aiosqlite
import os

DATABASE_NAME = "bilibili_favorites.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DATABASE_NAME)

async def check_db_contents():
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
        return

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Check collections
            async with db.execute("SELECT COUNT(*) FROM collections") as cursor:
                collections_count = await cursor.fetchone()
                print(f"Number of collections: {collections_count[0] if collections_count else 'Error or N/A'}")

            # Check videos
            async with db.execute("SELECT COUNT(*) FROM videos") as cursor:
                videos_count = await cursor.fetchone()
                print(f"Number of videos: {videos_count[0] if videos_count else 'Error or N/A'}")

            # Optionally, fetch a few sample records
            async with db.execute("SELECT * FROM collections LIMIT 3") as cursor:
                sample_collections = await cursor.fetchall()
                if sample_collections:
                    print("Sample collections:")
                    for row in sample_collections:
                        print(dict(row))
                else:
                    print("No sample collections found.")
            
            async with db.execute("SELECT * FROM videos LIMIT 3") as cursor:
                sample_videos = await cursor.fetchall()
                if sample_videos:
                    print("Sample videos:")
                    for row in sample_videos:
                        print(dict(row))
                else:
                    print("No sample videos found.")


    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    asyncio.run(check_db_contents())
