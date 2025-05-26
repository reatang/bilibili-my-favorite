import asyncio
from bilibili_api import favorite_list, Credential, select_client, request_settings
from rich import print
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import httpx # Import httpx
import shutil # For saving file from response

# Import database functions
import database 

load_dotenv()
select_client("curl_cffi")
request_settings.set("impersonate", "chrome136")


uid = os.getenv("USER_DEDE_USER_ID")
COVERS_DIR = "covers" # Define covers directory

# Instantiate Credential class
credential = Credential(
    sessdata=os.getenv("USER_SESSDATA"),
    bili_jct=os.getenv("USER_BILI_JCT"),
    buvid3=os.getenv("USER_BUVID3"),
    ac_time_value=os.getenv("USER_AC_TIME_VALUE"),
)

async def download_cover(bvid: str, cover_url: str) -> str | None:
    """Downloads a cover image and saves it locally."""
    if not cover_url or not cover_url.startswith("http"):
        print(f"  [COVER SKIP] Invalid cover URL for BVID {bvid}: {cover_url}")
        return None

    # Ensure protocol is present, default to https if missing (though Bilibili URLs usually have it)
    if cover_url.startswith("//"):
        cover_url = "https:" + cover_url
    
    local_cover_filename = f"{bvid}.jpg" # Or extract extension from URL if varied
    local_cover_path = os.path.join(COVERS_DIR, local_cover_filename)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(cover_url, timeout=10) # Timeout for download
            response.raise_for_status() # Raise an exception for bad status codes
            
            with open(local_cover_path, "wb") as f:
                f.write(response.content)
            print(f"  [COVER DOWNLOAD] Successfully downloaded cover for BVID {bvid} to {local_cover_path}")
            return local_cover_path
    except httpx.HTTPStatusError as e:
        print(f"  [COVER ERROR] HTTP error downloading cover for BVID {bvid} ({cover_url}): {e.response.status_code} - {e.response.text[:100]}")
    except httpx.RequestError as e:
        print(f"  [COVER ERROR] Request error downloading cover for BVID {bvid} ({cover_url}): {e}")
    except Exception as e:
        print(f"  [COVER ERROR] General error downloading cover for BVID {bvid} ({cover_url}): {e}")
    return None

# fetch_all_favorite_medias remains the same as in the previous step's subtask

async def fetch_all_favorite_medias(favorite_id: int, credential_instance: Credential) -> list[dict]:
    """Fetches all media items from all pages of a Bilibili favorite list."""
    has_more = True
    page = 1
    all_medias = []
    print(f"Fetching all pages for favorite ID: {favorite_id}...")
    while has_more:
        try:
            result = await favorite_list.get_video_favorite_list_content(
                media_id=favorite_id, page=page, credential=credential_instance
            )
            if not result["medias"]:
                print(f"No more medias found for favorite {favorite_id} on page {page}.")
                break
            
            all_medias.extend(result["medias"])
            print(f"Fetched page {page} for favorite {favorite_id}, {len(result['medias'])} items. Total: {len(all_medias)}")
            
            has_more = result["has_more"]
            page += 1
            if page > 50: 
                print(f"[WARN] Exceeded 50 pages for favorite {favorite_id}. Stopping.")
                break
            await asyncio.sleep(0.5) 
        except Exception as e:
            print(f"[ERROR] Failed to fetch page {page} for favorite {favorite_id}: {e}")
            break 
    return all_medias

async def sync_favorites() -> None:
    """Syncs Bilibili favorites with the local SQLite database and downloads covers."""
    os.makedirs(COVERS_DIR, exist_ok=True) # Ensure covers directory exists
    await database.initialize_database() 

    try:
        api_collections_response = await favorite_list.get_video_favorite_list(uid=uid, credential=credential)
        if not api_collections_response or not api_collections_response.get("list"):
            print("[ERROR] Could not fetch favorite lists from API or no lists found.")
            return
    except Exception as e:
        print(f"[ERROR] Failed to fetch favorite lists from API: {e}")
        return

    api_collections = api_collections_response["list"]
    run_time = datetime.now(timezone.utc)

    for fav_data in api_collections:
        bilibili_fid = str(fav_data["id"]) 
        title = fav_data["title"]
        print(f"Processing collection: {title} (FID: {bilibili_fid})")

        db_collection_id = await database.get_or_create_collection(bilibili_fid, title)
        api_media_list = await fetch_all_favorite_medias(int(bilibili_fid), credential)

        if not api_media_list:
            print(f"No media items found via API for collection: {title}. Skipping video processing.")
            await database.update_collection_sync_time(db_collection_id)
            continue

        db_videos_dict = await database.get_videos_by_collection_id(db_collection_id)
        api_bvids_seen = set()

        for video_item in api_media_list:
            bvid = video_item["bv_id"]
            api_bvids_seen.add(bvid)
            
            local_cover_path = None # Initialize before potential download
            # Download cover only if video is not "已失效视频"
            # and if it's a new video OR an existing video whose cover_url might have changed or wasn't downloaded.
            # For simplicity, we can attempt download if local_cover_path is not already set in DB,
            # or if cover_url changed.
            
            existing_db_video_data = db_videos_dict.get(bvid)
            should_download_cover = False

            if video_item["title"] != "已失效视频":
                if existing_db_video_data: # Existing video
                    if not existing_db_video_data.get("local_cover_path") or existing_db_video_data.get("cover_url") != video_item["cover"]:
                        should_download_cover = True
                else: # New video
                    should_download_cover = True
            
            if should_download_cover and video_item.get("cover"):
                print(f"  Attempting cover download for: {video_item['title']} (BVID: {bvid})")
                local_cover_path = await download_cover(bvid, video_item["cover"])

            if bvid in db_videos_dict:
                db_video = db_videos_dict[bvid]
                print(f"  Updating video: {video_item['title']} (BVID: {bvid})")
                # Pass local_cover_path, it will be None if download failed/skipped or if it's an existing video and cover didn't need update.
                # The database.update_video function needs to handle `local_cover_path=None` correctly (i.e., not update the field if None).
                # The version of database.py from previous step's subtask should handle this.
                await database.update_video(db_video["id"], video_item, run_time, db_video, local_cover_path=local_cover_path if local_cover_path else db_video.get("local_cover_path"))
                if db_video["title"] != "已失效视频" and video_item["title"] == "已失效视频":
                    print(f"  [STATUS CHANGE] Video '{db_video['title']}' (BVID: {bvid}) in collection '{title}' became unavailable.")
                elif db_video["is_deleted"] and video_item["title"] != "已失效视频":
                     print(f"  [STATUS CHANGE] Video '{video_item['title']}' (BVID: {bvid}) in collection '{title}' became available again.")
            else:
                print(f"  Adding new video: {video_item['title']} (BVID: {bvid})")
                await database.add_video(db_collection_id, video_item, run_time, local_cover_path=local_cover_path)
                if video_item["title"] == "已失效视频":
                    print(f"  [NEW UNAVAILABLE] New video '{video_item['title']}' (BVID: {bvid}) in collection '{title}' is unavailable.")
        
        for bvid, db_video in db_videos_dict.items():
            if bvid not in api_bvids_seen and not db_video["is_deleted"]:
                print(f"  Marking as deleted (not in API anymore): {db_video['title']} (BVID: {bvid})")
                await database.mark_video_as_deleted_by_bvid(bvid, db_collection_id, run_time)
                print(f"  [DELETED FROM BILIBILI] Video '{db_video['title']}' (BVID: {bvid}) in collection '{title}' was removed from Bilibili favorites.")
        
        await database.update_collection_sync_time(db_collection_id)
        print(f"Finished processing collection: {title}")

    print("Favorite synchronization complete.")

async def main():
    await sync_favorites()

if __name__ == "__main__":
    required_env_vars = ["USER_DEDE_USER_ID", "USER_SESSDATA", "USER_BILI_JCT", "USER_BUVID3"]
    if not all(os.getenv(var) for var in required_env_vars):
        print(f"Error: Missing one or more required environment variables: {', '.join(required_env_vars)}")
        print("Please ensure your .env file is correctly set up.")
    else:
        asyncio.run(main())
