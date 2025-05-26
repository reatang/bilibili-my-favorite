import os
import urllib.parse
from fastapi import FastAPI, HTTPException, Query, Request # Add Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates # Add Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse # Add HTMLResponse
from typing import List, Optional, Dict, Any
import aiosqlite # Ensure aiosqlite is available

# Assuming database.py is in the same directory
import database 

# Initialize FastAPI app
app = FastAPI(
    title="Bilibili Favorites API",
    description="API for accessing locally synced Bilibili favorites and their covers.",
    version="0.1.0"
)

# --- Configuration ---
COVERS_DIR = "covers"
DATABASE_PATH = database.DB_PATH # Use DB_PATH from database.py
TEMPLATES_DIR = "templates"
# STATIC_DIR = "static" # If you add separate static files later

# --- Template Engine Setup ---
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- Pydantic Models (Optional but good practice) ---
# For now, we'll use Dict[str, Any] for simplicity in responses,
# but Pydantic models would be better for production.

# Example Pydantic models (can be expanded later):
# from pydantic import BaseModel, Field
# class Collection(BaseModel):
#     id: int
#     bilibili_fid: str
#     title: str
#     last_synced: Optional[datetime]

# class Video(BaseModel):
#     id: int
#     bvid: str
#     collection_id: int
#     title: str
#     # ... other fields

# --- Database Helper ---
async def get_db():
    # Using the get_db_connection from database.py
    # This simple approach creates a new connection per request that uses it.
    # For more complex scenarios, FastAPI's dependency injection with startup/shutdown events
    # to manage a connection pool (e.g., using databases library) might be better.
    db = await database.get_db_connection()
    try:
        yield db
    finally:
        await db.close()

# --- Static Files Mounting ---
# Mount covers directory to serve images
if os.path.exists(COVERS_DIR) and os.path.isdir(COVERS_DIR):
    app.mount("/covers", StaticFiles(directory=COVERS_DIR), name="covers")
else:
    print(f"[WARNING] Covers directory '{COVERS_DIR}' not found. Cover images will not be served.")
    # Optionally, create it here if desired: os.makedirs(COVERS_DIR, exist_ok=True)
    # However, main.py should be responsible for creating it during sync.
# if os.path.exists(STATIC_DIR) and os.path.isdir(STATIC_DIR):
#    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# else:
#    os.makedirs(STATIC_DIR, exist_ok=True) # Create static if it doesn't exist for convenience
#    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Web Page Endpoints ---
@app.get("/", response_class=HTMLResponse, summary="Display list of collections")
async def read_root(request: Request):
    # This endpoint serves the main page (index.html)
    # The actual data loading is done client-side via JavaScript calling /api/collections
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/view/collection/{collection_db_id}", response_class=HTMLResponse, summary="Display videos in a collection")
async def view_collection_videos(request: Request, collection_db_id: int):
    # This endpoint serves the collection detail page
    # Data is loaded client-side by JavaScript. We pass collection_id for potential use in template if needed.
    # We also need to verify collection_db_id exists to give a proper 404 if not.
    async with database.get_db_connection() as db:
        cursor = await db.execute("SELECT title FROM collections WHERE id = ?", (collection_db_id,))
        collection = await cursor.fetchone()
        if not collection:
            # Optionally, render a generic error page or redirect
            return templates.TemplateResponse("error_404.html", {"request": request, "message": f"Collection with ID {collection_db_id} not found."}, status_code=404)
    
    return templates.TemplateResponse("collection_detail.html", {"request": request, "collection_id": collection_db_id, "collection_title": collection["title"] if collection else "Collection"})


# --- API Endpoints ---

@app.get("/api/collections", summary="List all collections", response_model=List[Dict[str, Any]])
async def get_all_collections():
    async with database.get_db_connection() as db: # Simpler connection management for now
        cursor = await db.execute("SELECT id, bilibili_fid, title, last_synced FROM collections ORDER BY title")
        collections = await cursor.fetchall()
        return [dict(row) for row in collections]

@app.get("/api/collections/{collection_db_id}/videos", summary="List videos for a specific collection", response_model=List[Dict[str, Any]])
async def get_videos_for_collection(
    collection_db_id: int,
    status: Optional[str] = Query(None, enum=["all", "available", "deleted"]),
    search: Optional[str] = Query(None, min_length=1)
):
    base_query = "SELECT id, bvid, collection_id, title, up_name, up_mid, cover_url, local_cover_path, first_seen, last_seen, is_deleted, deleted_at FROM videos WHERE collection_id = ?"
    params: list[Any] = [collection_db_id]

    if status == "available":
        base_query += " AND is_deleted = FALSE"
    elif status == "deleted":
        base_query += " AND is_deleted = TRUE"
    
    if search:
        base_query += " AND title LIKE ?"
        params.append(f"%{search}%")
    
    base_query += " ORDER BY last_seen DESC"

    async with database.get_db_connection() as db:
        cursor = await db.execute("SELECT 1 FROM collections WHERE id = ?", (collection_db_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Collection with internal DB ID {collection_db_id} not found.")
        
        cursor = await db.execute(base_query, tuple(params))
        videos = await cursor.fetchall()
        
        # Ensure local_cover_path is relative to /covers/ if served that way, or provide full path if client constructs URL
        # For now, just return the path as stored. Client will prepend /covers/
        return [dict(row) for row in videos]


@app.get("/api/videos/by_bvid/{bvid}", summary="Get video details by BVID", response_model=List[Dict[str, Any]])
async def get_video_by_bvid(bvid: str):
    # A video can be in multiple collections, so this might return multiple entries.
    async with database.get_db_connection() as db:
        cursor = await db.execute("""
            SELECT v.id, v.bvid, v.collection_id, c.title as collection_title, v.title, 
                   v.up_name, v.up_mid, v.cover_url, v.local_cover_path, 
                   v.first_seen, v.last_seen, v.is_deleted, v.deleted_at 
            FROM videos v
            JOIN collections c ON v.collection_id = c.id
            WHERE v.bvid = ?
            ORDER BY v.last_seen DESC
        """, (bvid,))
        videos = await cursor.fetchall()
        if not videos:
            raise HTTPException(status_code=404, detail=f"Video with BVID {bvid} not found in any collection.")
        return [dict(row) for row in videos]

@app.get("/api/videos/{video_db_id}/details", summary="Get specific video details by its database ID", response_model=Dict[str, Any])
async def get_video_by_db_id(video_db_id: int):
    async with database.get_db_connection() as db:
        cursor = await db.execute("""
            SELECT v.id, v.bvid, v.collection_id, c.title as collection_title, v.title, 
                   v.up_name, v.up_mid, v.cover_url, v.local_cover_path, 
                   v.first_seen, v.last_seen, v.is_deleted, v.deleted_at 
            FROM videos v
            JOIN collections c ON v.collection_id = c.id
            WHERE v.id = ?
        """, (video_db_id,))
        video = await cursor.fetchone()
        if not video:
            raise HTTPException(status_code=404, detail=f"Video with database ID {video_db_id} not found.")
        return dict(video)
        
# The StaticFiles mount for /covers handles serving images directly.
# If a more direct FileResponse is needed for some reason, an endpoint like this could be used,
# but StaticFiles is generally preferred for directories.
@app.get("/cover_img/{image_filename}", summary="Serve a single cover image (alternative to StaticFiles)")
async def get_cover_image_direct(image_filename: str):
    # Basic security: prevent path traversal
    if ".." in image_filename or image_filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    
    file_path = os.path.join(COVERS_DIR, image_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found.")
    
    # URL encode the filename part of the path if it contains special characters
    # However, image_filename from path param should already be decoded.
    # For display in HTML, ensure URLs are properly encoded if filenames can have spaces, etc.
    return FileResponse(file_path)


if __name__ == "__main__":
    import uvicorn
    # This is for local development. For deployment, use a proper ASGI server like Uvicorn/Hypercorn directly.
    # Example: uvicorn web_server:app --reload --host 0.0.0.0 --port 8000
    print(f"Attempting to run Uvicorn server for web_server:app on port 8000")
    print(f"Database is expected at: {DATABASE_PATH}")
    print(f"Covers directory is expected at: {COVERS_DIR}")
    if not os.path.exists(DATABASE_PATH):
        print(f"[ERROR] Database file not found at {DATABASE_PATH}. Please run main.py to sync/create it.")
    
    # Check if StaticFiles mounting path exists
    if not (os.path.exists(COVERS_DIR) and os.path.isdir(COVERS_DIR)):
         print(f"[WARNING] Covers directory '{COVERS_DIR}' not found or is not a directory. Static file serving for covers might fail.")
         print("Attempting to create it...")
         os.makedirs(COVERS_DIR, exist_ok=True) # Attempt to create if missing for dev convenience

    uvicorn.run(app, host="0.0.0.0", port=8000)
