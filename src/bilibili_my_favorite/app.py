"""
FastAPI应用程序主文件
整合所有模块，提供Web API服务
"""
import os
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from bilibili_my_favorite.core.config import config
from bilibili_my_favorite.utils.logger import logger
from bilibili_my_favorite.api.collections import router as collections_router
from bilibili_my_favorite.api.videos import router as videos_router
from bilibili_my_favorite.dao.base import BaseDAO

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


# 创建FastAPI应用
app = FastAPI(
    title="B站收藏夹管理系统",
    description="本地同步和管理B站收藏夹的Web应用",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置模板引擎
templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))

# 挂载静态文件
if config.COVERS_DIR.exists():
    app.mount("/covers", StaticFiles(directory=str(config.COVERS_DIR)), name="covers")
    logger.info(f"已挂载封面目录: {config.COVERS_DIR}")
else:
    logger.warning(f"封面目录不存在: {config.COVERS_DIR}")

# 注册API路由
app.include_router(collections_router)
app.include_router(videos_router)


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("B站收藏夹管理系统启动中...")
    
    # 初始化数据库连接
    try:
        await BaseDAO.initialize_database()
        logger.info("数据库连接初始化成功")
        
        # 检查并执行数据库迁移
        from .models.database_migration import check_migration_needed, migrate_database
        if await check_migration_needed():
            logger.info("检测到需要数据库迁移，开始执行...")
            await migrate_database()
            logger.info("数据库迁移完成")
        
    except Exception as e:
        logger.error(f"数据库初始化或迁移失败: {e}")
        raise
    
    # 确保必要目录存在
    config.ensure_actual_directories()
    
    # 检查B站凭据
    if not config.validate_bilibili_credentials():
        logger.warning("B站API凭据不完整，同步功能可能无法正常工作")
    
    logger.info("应用启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("B站收藏夹管理系统正在关闭...")
    
    # 关闭数据库连接
    try:
        await BaseDAO.close_database()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接时出错: {e}")
    
    logger.info("应用关闭完成")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """404错误处理"""
    if request.url.path.startswith("/api/"):
        # API请求返回JSON
        return {"error": "Not Found", "detail": exc.detail}
    else:
        # 页面请求返回HTML
        return templates.TemplateResponse(
            "error_404.html", 
            {"request": request, "message": exc.detail},
            status_code=404
        )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """500错误处理"""
    logger.error(f"内部服务器错误: {exc}")
    if request.url.path.startswith("/api/"):
        # API请求返回JSON
        return {"error": "Internal Server Error", "detail": "服务器内部错误"}
    else:
        # 页面请求返回HTML
        return templates.TemplateResponse(
            "error_500.html",
            {"request": request, "message": "服务器内部错误"},
            status_code=500
        )


# Web页面路由
@app.get("/", response_class=HTMLResponse, summary="首页")
async def index(request: Request):
    """显示收藏夹列表页面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/collections/{collection_id}", response_class=HTMLResponse, summary="收藏夹详情页")
async def collection_detail(request: Request, collection_id: int):
    """显示收藏夹详情页面"""
    # 这里可以预先获取收藏夹信息用于页面标题等
    try:
        from .dao.collection_dao import collection_dao
        collection = await collection_dao.get_collection_by_id(collection_id)
        if not collection:
            return templates.TemplateResponse(
                "error_404.html",
                {"request": request, "message": f"收藏夹 {collection_id} 不存在"},
                status_code=404
            )
        
        return templates.TemplateResponse(
            "collection_detail.html",
            {
                "request": request,
                "collection_id": collection_id,
                "collection_title": collection["title"]
            }
        )
    except Exception as e:
        logger.error(f"获取收藏夹 {collection_id} 信息失败: {e}")
        return templates.TemplateResponse(
            "error_500.html",
            {"request": request, "message": "获取收藏夹信息失败"},
            status_code=500
        )


@app.get("/sync", response_class=HTMLResponse, summary="同步页面")
async def sync_page(request: Request):
    """显示同步管理页面"""
    return templates.TemplateResponse("sync.html", {"request": request})


@app.get("/stats", response_class=HTMLResponse, summary="统计页面")
async def stats_page(request: Request):
    """显示统计信息页面"""
    return templates.TemplateResponse("stats.html", {"request": request})


# 健康检查端点
@app.get("/health", summary="健康检查")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "database": str(config.DATABASE_PATH),
        "covers_dir": str(config.COVERS_DIR),
        "bilibili_auth": config.validate_bilibili_credentials()
    }


# 应用信息端点
@app.get("/info", summary="应用信息")
async def app_info():
    """获取应用信息"""
    return {
        "name": "B站收藏夹管理系统",
        "version": "1.0.0",
        "description": "本地同步和管理B站收藏夹的Web应用",
        "config": {
            "database_path": str(config.DATABASE_PATH),
            "covers_dir": str(config.COVERS_DIR),
            "templates_dir": str(config.TEMPLATES_DIR),
            "log_level": config.LOG_LEVEL,
            "bilibili_auth_configured": config.validate_bilibili_credentials()
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"启动Web服务器: {config.WEB_HOST}:{config.WEB_PORT}")
    uvicorn.run(
        "src.app:app",
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    ) 