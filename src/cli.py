"""
命令行工具
提供同步和管理功能的CLI接口
"""
import asyncio
import json
import sys
import traceback
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from bilibili_my_favorite.core.config import config
from bilibili_my_favorite.services.bilibili_service import bilibili_service
from bilibili_my_favorite.services.optimized_sync_service import optimized_sync_service
from bilibili_my_favorite.dao.collection_dao import collection_dao
from bilibili_my_favorite.dao.video_dao import video_dao
from bilibili_my_favorite.dao.base import BaseDAO
from bilibili_my_favorite.utils.logger import logger
from bilibili_my_favorite.utils.downloader import video_downloader
from bilibili_my_favorite.services.sync_context import SyncContext

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


console = Console()


def async_command(f):
    """异步命令装饰器，自动处理数据库生命周期"""
    def wrapper(*args, **kwargs):
        async def run_with_db():
            try:
                # 初始化数据库连接
                await BaseDAO.initialize_database()
                # 运行原始函数
                return await f(*args, **kwargs)
            except Exception as e:
                error_traceback = traceback.format_exc()
                console.print(f"[bold red]执行失败: {e}[/bold red]")
                logger.error(f"命令执行失败: {e}\n错误栈:\n{error_traceback}")
                raise
            finally:
                # 关闭数据库连接
                try:
                    await BaseDAO.close_database()
                except Exception as e:
                    logger.error(f"关闭数据库连接时出错: {e}")
        
        return asyncio.run(run_with_db())
    return wrapper


@click.group()
@click.option('--debug', is_flag=True, help='启用调试模式')
def cli(debug: bool):
    """B站收藏夹管理系统命令行工具
    
    主要功能：
    - sync: 同步收藏夹数据
    - download: 下载B站视频
    - list-*: 查看各种列表信息
    - stats: 显示统计信息
    - serve: 启动Web服务器
    - init-db: 初始化数据库
    - clean: 清理中断的同步任务
    """
    if debug:
        config.LOG_LEVEL = "DEBUG"
        logger.setLevel("DEBUG")


@cli.command()
@click.option('--collection-id', '-c', help='指定收藏夹ID，为空则同步所有')
@click.option('--force', '-f', is_flag=True, help='强制重新下载封面')
def sync(collection_id: Optional[str], force: bool):
    """同步收藏夹数据（默认使用优化模式，支持中断恢复）"""
    @async_command
    async def run_sync():
        # 检查B站凭据
        if not bilibili_service.is_authenticated():
            console.print("[bold red]错误: B站API凭据不完整[/bold red]")
            console.print("请检查 .env 文件中的以下配置:")
            console.print("- USER_DEDE_USER_ID")
            console.print("- USER_SESSDATA")
            console.print("- USER_BILI_JCT")
            console.print("- USER_BUVID3")
            return
        
        # 使用优化同步方式（默认）
        try:
            # 检查是否有中断的任务
            lock_file = SyncContext.find_existing_lock_file()
            
            if lock_file:
                console.print("[bold yellow]发现中断的同步任务，继续执行...[/bold yellow]")
                # 从锁文件加载任务ID
                context = SyncContext.load_from_lock_file(lock_file)
                task_id = context.task_id
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("恢复同步中...", total=None)
                    stats = await optimized_sync_service.resume_sync_task(task_id)
                    progress.update(task, completed=True)
            else:
                console.print("[bold blue]开始优化同步收藏夹数据...[/bold blue]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("同步中...", total=None)
                    
                    if collection_id:
                        stats = await optimized_sync_service.sync_single_collection(collection_id)
                    else:
                        stats = await optimized_sync_service.sync_all_favorites()
                    
                    progress.update(task, completed=True)
        except Exception as e:
            error_traceback = traceback.format_exc()
            console.print(f"[bold red]同步失败: {e}[/bold red]")
            logger.error(f"同步失败: {e}\n错误栈:\n{error_traceback}")
            return
        
        # 显示同步结果
        console.print("\n[bold green]同步完成![/bold green]")
         
        table = Table(title="同步统计")
        table.add_column("项目", style="cyan")
        table.add_column("数量", style="magenta")
        
        table.add_row("处理的收藏夹", str(stats["collections_processed"]))
        table.add_row("新增视频", str(stats["videos_added"]))
        table.add_row("更新视频", str(stats["videos_updated"]))
        table.add_row("删除视频", str(stats["videos_deleted"]))
        table.add_row("下载封面", str(stats["covers_downloaded"]))
        
        console.print(table)
        
        # 显示被删除的视频详情
        if stats.get("deleted_videos"):
            console.print(f"\n[bold yellow]发现 {len(stats['deleted_videos'])} 个被删除的视频[/bold yellow]")
            for deleted_video in stats["deleted_videos"][:5]:  # 只显示前5个
                console.print(f"  • {deleted_video['title']} (BVID: {deleted_video['bvid']}) - 来自收藏夹: {deleted_video['collection_title']}")
            if len(stats["deleted_videos"]) > 5:
                console.print(f"  ... 还有 {len(stats['deleted_videos']) - 5} 个被删除的视频")
        
        if stats["errors"]:
            console.print(f"\n[bold yellow]警告: 发生了 {len(stats['errors'])} 个错误[/bold yellow]")
            for error in stats["errors"][:5]:  # 只显示前5个错误
                console.print(f"  • {error}")
            if len(stats["errors"]) > 5:
                console.print(f"  ... 还有 {len(stats['errors']) - 5} 个错误")
    
    run_sync()


@cli.command()
def list_collections():
    """列出所有收藏夹"""
    @async_command
    async def run_list():
        try:
            collections = await collection_dao.get_all_collections()
            
            if not collections:
                console.print("[yellow]没有找到收藏夹数据[/yellow]")
                console.print("请先运行 'sync' 命令同步数据")
                return
            
            table = Table(title="收藏夹列表")
            table.add_column("ID", style="cyan")
            table.add_column("B站ID", style="blue")
            table.add_column("标题", style="green")
            table.add_column("视频数", style="magenta")
            table.add_column("最后同步", style="yellow")
            
            for collection in collections:
                last_synced = collection.get("last_synced", "未同步")
                if last_synced and last_synced != "未同步":
                    last_synced = last_synced[:19]  # 只显示日期时间部分
                
                table.add_row(
                    str(collection["id"]),
                    collection["bilibili_fid"],
                    collection["title"],
                    str(collection.get("media_count", 0)),
                    last_synced
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[bold red]获取收藏夹列表失败: {e}[/bold red]")
    
    run_list()


@cli.command()
@click.argument('collection_id', type=int)
@click.option('--status', '-s', type=click.Choice(['all', 'available', 'deleted']), 
              default='all', help='视频状态过滤')
@click.option('--limit', '-l', type=int, default=20, help='显示数量限制')
def list_videos(collection_id: int, status: str, limit: int):
    """列出收藏夹中的视频"""
    @async_command
    async def run_list():
        try:
            # 检查收藏夹是否存在
            collection = await collection_dao.get_collection_by_id(collection_id)
            if not collection:
                console.print(f"[bold red]收藏夹 {collection_id} 不存在[/bold red]")
                return
            
            console.print(f"[bold blue]收藏夹: {collection['title']}[/bold blue]")
            
            videos = await video_dao.get_videos_by_collection(
                collection_id=collection_id,
                status=status,
                limit=limit
            )
            
            if not videos:
                console.print("[yellow]没有找到视频[/yellow]")
                return
            
            table = Table(title=f"视频列表 ({status})")
            table.add_column("ID", style="cyan")
            table.add_column("BVID", style="blue")
            table.add_column("标题", style="green", max_width=50)
            table.add_column("UP主", style="magenta")
            table.add_column("状态", style="yellow")
            table.add_column("最后更新", style="dim")
            
            for video in videos:
                status_text = "已删除" if video["is_deleted"] else "正常"
                last_seen = video.get("last_seen", "")
                if last_seen:
                    last_seen = last_seen[:19]  # 只显示日期时间部分
                
                table.add_row(
                    str(video["id"]),
                    video["bvid"],
                    video["title"][:47] + "..." if len(video["title"]) > 50 else video["title"],
                    video["uploader_name"],
                    status_text,
                    last_seen
                )
            
            console.print(table)
            
            if len(videos) == limit:
                console.print(f"[dim]显示了前 {limit} 个视频，使用 --limit 参数查看更多[/dim]")
            
        except Exception as e:
            console.print(f"[bold red]获取视频列表失败: {e}[/bold red]")
    
    run_list()


@cli.command()
def stats():
    """显示统计信息"""
    @async_command
    async def run_stats():
        try:
            collections = await collection_dao.get_all_collections()
            
            if not collections:
                console.print("[yellow]没有找到数据[/yellow]")
                return
            
            # 计算总体统计
            total_collections = len(collections)
            total_videos = 0
            total_available = 0
            total_deleted = 0
            total_official = 0
            total_normal = 0
            
            for collection in collections:
                stats = await collection_dao.get_collection_stats(collection["id"])
                total_videos += stats.get("total_videos", 0)
                total_available += stats.get("available_videos", 0)
                total_deleted += stats.get("deleted_videos", 0)
                
                # 获取视频类型统计
                type_stats = await video_dao.get_video_type_stats(collection["id"])
                total_official += type_stats.get("official_videos", 0)
                total_normal += type_stats.get("normal_videos", 0)
            
            # 显示总体统计
            table = Table(title="系统统计")
            table.add_column("项目", style="cyan")
            table.add_column("数量", style="magenta")
            
            table.add_row("收藏夹总数", str(total_collections))
            table.add_row("视频总数", str(total_videos))
            table.add_row("可用视频", str(total_available))
            table.add_row("已删除视频", str(total_deleted))
            table.add_row("普通视频", str(total_normal))
            table.add_row("官方影视作品", str(total_official))
            
            console.print(table)
            
            # 显示各收藏夹统计
            if total_collections > 0:
                console.print("\n")
                detail_table = Table(title="收藏夹详细统计")
                detail_table.add_column("收藏夹", style="green")
                detail_table.add_column("总视频", style="cyan")
                detail_table.add_column("可用", style="blue")
                detail_table.add_column("已删除", style="red")
                detail_table.add_column("官方影视", style="yellow")
                detail_table.add_column("删除率", style="dim")
                
                for collection in collections[:10]:  # 只显示前10个
                    stats = await collection_dao.get_collection_stats(collection["id"])
                    type_stats = await video_dao.get_video_type_stats(collection["id"])
                    
                    total = stats.get("total_videos", 0)
                    deleted = stats.get("deleted_videos", 0)
                    available = stats.get("available_videos", 0)
                    official = type_stats.get("official_videos", 0)
                    
                    delete_rate = f"{(deleted / total * 100):.1f}%" if total > 0 else "0%"
                    
                    detail_table.add_row(
                        collection["title"][:25] + "..." if len(collection["title"]) > 28 else collection["title"],
                        str(total),
                        str(available),
                        str(deleted),
                        str(official),
                        delete_rate
                    )
                
                console.print(detail_table)
                
                if total_collections > 10:
                    console.print(f"[dim]还有 {total_collections - 10} 个收藏夹未显示[/dim]")
            
        except Exception as e:
            console.print(f"[bold red]获取统计信息失败: {e}[/bold red]")
    
    run_stats()


@cli.command()
@click.option('--host', default='127.0.0.1', help='服务器地址')
@click.option('--port', default=8000, help='服务器端口')
@click.option('--reload', is_flag=True, help='启用自动重载')
def serve(host: str, port: int, reload: bool):
    """启动Web服务器"""
    import uvicorn
    
    console.print(f"[bold blue]启动Web服务器: http://{host}:{port}[/bold blue]")
    console.print("按 Ctrl+C 停止服务器")
    
    try:
        uvicorn.run(
            "bilibili_my_favorite.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level=config.LOG_LEVEL.lower()
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]服务器已停止[/yellow]")


@cli.command()
def init_db():
    """初始化数据库"""
    @async_command
    async def run_init():
        try:
            console.print("[bold blue]初始化数据库...[/bold blue]")
            
            # 初始化数据库
            from bilibili_my_favorite.models.database import initialize_database
            await initialize_database()
            
            # 检查并执行迁移
            from bilibili_my_favorite.models.database_migration import check_migration_needed, migrate_database
            if await check_migration_needed():
                console.print("[bold yellow]检测到需要数据库迁移，开始执行...[/bold yellow]")
                await migrate_database()
                console.print("[bold green]数据库迁移完成![/bold green]")
            
            console.print("[bold green]数据库初始化完成![/bold green]")
            console.print(f"数据库文件: {config.DATABASE_PATH}")
        except Exception as e:
            console.print(f"[bold red]数据库初始化失败: {e}[/bold red]")
    
    run_init()


@cli.command()
@click.option('--collection-id', '-c', type=int, help='指定收藏夹ID')
@click.option('--limit', '-l', type=int, default=20, help='显示数量限制')
def list_official(collection_id: Optional[int], limit: int):
    """列出官方影视作品"""
    @async_command
    async def run_list():
        try:
            # 获取官方影视作品
            videos = await video_dao.get_official_videos(
                collection_id=collection_id,
                limit=limit
            )
            
            if not videos:
                if collection_id:
                    console.print(f"[yellow]收藏夹 {collection_id} 中没有找到官方影视作品[/yellow]")
                else:
                    console.print("[yellow]没有找到官方影视作品[/yellow]")
                return
            
            # 显示收藏夹信息
            if collection_id:
                collection = await collection_dao.get_collection_by_id(collection_id)
                if collection:
                    console.print(f"[bold blue]收藏夹: {collection['title']}[/bold blue]")
            
            table = Table(title="官方影视作品列表")
            table.add_column("BVID", style="blue")
            table.add_column("标题", style="green", max_width=40)
            table.add_column("UP主", style="magenta")
            table.add_column("状态", style="yellow")
            table.add_column("类型", style="cyan")
            
            for video in videos:
                status_text = "已删除" if video["is_deleted"] else "正常"
                
                # 解析ogv_info来判断类型
                ogv_type = "官方影视"
                try:
                    if video["ogv_info"]:
                        ogv_data = json.loads(video["ogv_info"])
                        if "movie" in str(ogv_data).lower():
                            ogv_type = "电影"
                        elif "tv" in str(ogv_data).lower() or "episode" in str(ogv_data).lower():
                            ogv_type = "电视剧"
                        elif "documentary" in str(ogv_data).lower():
                            ogv_type = "纪录片"
                except:
                    pass
                
                table.add_row(
                    video["bvid"],
                    video["title"][:37] + "..." if len(video["title"]) > 40 else video["title"],
                    video["uploader_name"],
                    status_text,
                    ogv_type
                )
            
            console.print(table)
            
            if len(videos) == limit:
                console.print(f"[dim]显示了前 {limit} 个官方影视作品，使用 --limit 参数查看更多[/dim]")
            
        except Exception as e:
            console.print(f"[bold red]获取官方影视作品列表失败: {e}[/bold red]")
    
    run_list()


@cli.command()
@click.option('--limit', '-l', type=int, default=20, help='显示数量限制')
def list_deleted(limit: int):
    """列出最近被删除的视频"""
    @async_command
    async def run_list():
        try:
            # 查询删除日志
            from bilibili_my_favorite.dao.base import BaseDAO
            
            query = """
            SELECT dl.video_bvid, dl.video_title, dl.uploader_name, 
                   dl.deleted_at, dl.reason, c.title as collection_title
            FROM deletion_logs dl
            JOIN collections c ON dl.collection_id = c.id
            ORDER BY dl.deleted_at DESC
            LIMIT ?
            """
            
            # 使用BaseDAO执行查询
            dao = BaseDAO()
            rows = await dao.execute_query(query, (limit,))
            deleted_videos = dao.rows_to_dicts(rows)
            
            if not deleted_videos:
                console.print("[yellow]没有找到被删除的视频记录[/yellow]")
                return
            
            table = Table(title="最近被删除的视频")
            table.add_column("BVID", style="blue")
            table.add_column("标题", style="green", max_width=35)
            table.add_column("UP主", style="magenta")
            table.add_column("收藏夹", style="cyan", max_width=25)
            table.add_column("删除时间", style="yellow")
            table.add_column("原因", style="dim")
            
            for video in deleted_videos:
                deleted_time = video["deleted_at"][:19] if video["deleted_at"] else "未知"
                
                table.add_row(
                    video["video_bvid"],
                    video["video_title"][:32] + "..." if len(video["video_title"]) > 35 else video["video_title"],
                    video["uploader_name"] or "Unknown",
                    video["collection_title"][:22] + "..." if len(video["collection_title"]) > 25 else video["collection_title"],
                    deleted_time,
                    video["reason"] or "未知"
                )
            
            console.print(table)
            
            if len(deleted_videos) == limit:
                console.print(f"[dim]显示了最近 {limit} 个被删除的视频，使用 --limit 参数查看更多[/dim]")
            
        except Exception as e:
            console.print(f"[bold red]获取删除记录失败: {e}[/bold red]")
    
    run_list()


@cli.command()
def clean():
    """清理中断的同步任务（删除锁文件，保留历史数据）"""
    try:
        # 检查锁文件
        lock_file = config.DATA_DIR / "sync_lock.json"
        
        if not lock_file.exists():
            console.print("[yellow]没有找到中断的同步任务[/yellow]")
            return
        
        console.print("[bold blue]清理中断的同步任务...[/bold blue]")
        
        # 删除锁文件
        lock_file.unlink()
        console.print(f"删除锁文件: {lock_file}")
        console.print("[dim]历史数据目录已保留[/dim]")
        
        console.print("[bold green]清理完成![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]清理失败: {e}[/bold red]")


@cli.command()
@click.argument('bvid', type=str)
@click.option('--page', '-p', type=int, default=0, help='分P索引（从0开始）')
@click.option('--quality', '-q', type=int, default=80, help='视频质量（16=360P, 32=480P, 64=720P, 80=1080P, 112=1080P+）')
@click.option('--output', '-o', type=str, help='输出文件名（不含扩展名）')
@click.option('--ffmpeg-path', type=str, default='ffmpeg', help='FFmpeg可执行文件路径')
def download(bvid: str, page: int, quality: int, output: Optional[str], ffmpeg_path: str):
    """下载B站视频"""
    @async_command
    async def run_download():
        import os
        import traceback
        from bilibili_api import video
        from bilibili_my_favorite.core.bilibili_plus import get_download_url
        from bilibili_my_favorite.utils.downloader import video_downloader
        
        # 检查B站凭据
        if not bilibili_service.is_authenticated():
            console.print("[bold red]错误: B站API凭据不完整[/bold red]")
            console.print("请检查 .env 文件中的以下配置:")
            console.print("- USER_DEDE_USER_ID")
            console.print("- USER_SESSDATA")
            console.print("- USER_BILI_JCT")
            console.print("- USER_BUVID3")
            return
        
        # 检查FFmpeg
        try:
            import subprocess
            result = subprocess.run([ffmpeg_path, '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                console.print(f"[bold red]错误: FFmpeg不可用，请检查路径: {ffmpeg_path}[/bold red]")
                return
        except (subprocess.TimeoutExpired, FileNotFoundError):
            console.print(f"[bold red]错误: 找不到FFmpeg，请检查路径: {ffmpeg_path}[/bold red]")
            console.print("请安装FFmpeg或指定正确的路径")
            return
        
        try:
            console.print(f"[bold blue]开始下载视频: {bvid}[/bold blue]")
            
            credential = bilibili_service.credential
            
            # 实例化Video类
            v = video.Video(bvid=bvid, credential=credential)
            
            # 获取视频信息
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                info_task = progress.add_task("获取视频信息...", total=None)
                
                try:
                    info = await v.get_info()
                    progress.update(info_task, completed=True)
                except Exception as e:
                    progress.update(info_task, completed=True)
                    console.print(f"[bold red]获取视频信息失败: {e}[/bold red]")
                    return
            
            # 显示视频信息
            console.print(f"[green]视频标题:[/green] {info['title']}")
            console.print(f"[green]UP主:[/green] {info['owner']['name']}")
            console.print(f"[green]视频时长:[/green] {info['duration']}秒")
            console.print(f"[green]分P数量:[/green] {len(info['pages'])}")
            
            # 检查分P索引
            if page >= len(info['pages']):
                console.print(f"[bold red]错误: 分P索引 {page} 超出范围（0-{len(info['pages'])-1}）[/bold red]")
                return
            
            page_info = info['pages'][page]
            console.print(f"[green]当前分P:[/green] P{page+1} - {page_info['part']}")
            
            # 获取CID
            cid = page_info['cid']
            
            # 获取下载链接
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                url_task = progress.add_task("获取下载链接...", total=None)
                
                try:
                    download_url_data = await get_download_url(
                        bvid=bvid, cid=cid, credential=credential, qn=quality
                    )
                    progress.update(url_task, completed=True)
                except Exception as e:
                    progress.update(url_task, completed=True)
                    console.print(f"[bold red]获取下载链接失败: {e}[/bold red]")
                    return
            
            # 解析下载信息
            detecter = video.VideoDownloadURLDataDetecter(data=download_url_data)
            streams = detecter.detect_best_streams()
            
            if not streams:
                console.print("[bold red]错误: 未找到可用的视频流[/bold red]")
                return
            
            # 生成输出文件名
            if output:
                output_filename = output
            else:
                # 清理文件名中的非法字符
                safe_title = "".join(c for c in info['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
                output_filename = f"{bvid}_{safe_title}_P{page+1}"
            
            output_path = config.VIDEOS_DIR / f"{output_filename}.mp4"
            
            console.print(f"[green]输出路径:[/green] {output_path}")
            console.print(f"[green]视频质量:[/green] {download_url_data.get('quality', quality)}")
            
            # 下载视频
            if detecter.check_flv_mp4_stream():
                # FLV流下载
                temp_file_path = config.VIDEOS_DIR / f"{bvid}.temp.flv"
                
                console.print("[blue]检测到FLV流，开始下载...[/blue]")
                
                try:
                    await video_downloader.download_video(
                        streams[0].url, str(temp_file_path), "下载FLV音视频流"
                    )
                    
                    # 转换格式
                    console.print("[blue]转换视频格式...[/blue]")
                    convert_cmd = f'"{ffmpeg_path}" -i "{temp_file_path}" -c copy "{output_path}"'
                    result = os.system(convert_cmd)
                    
                    if result == 0:
                        console.print("[bold green]视频下载完成![/bold green]")
                    else:
                        console.print("[bold red]视频格式转换失败[/bold red]")
                    
                    # 删除临时文件
                    if temp_file_path.exists():
                        temp_file_path.unlink()
                        
                except Exception as e:
                    console.print(f"[bold red]下载失败: {e}[/bold red]")
                    if temp_file_path.exists():
                        temp_file_path.unlink()
                    return
            else:
                # MP4流下载（分离的视频和音频流）
                video_temp_path = config.VIDEOS_DIR / f"{bvid}.video_temp.m4s"
                audio_temp_path = config.VIDEOS_DIR / f"{bvid}.audio_temp.m4s"
                
                console.print("[blue]检测到分离的视频/音频流，开始下载...[/blue]")
                
                try:
                    if not video_temp_path.exists():
                        # 下载视频流
                        await video_downloader.download_video(
                            streams[0].url, str(video_temp_path), "下载视频流"
                        )
                    
                    # 下载音频流
                    if len(streams) > 1:
                        if not audio_temp_path.exists():
                            await video_downloader.download_video(
                                streams[1].url, str(audio_temp_path), "下载音频流"
                            )
                    
                    # 合并音视频
                    console.print("[blue]合并音视频流...[/blue]")
                    if len(streams) > 1:
                        merge_cmd = f"{ffmpeg_path} -i {video_temp_path} -i {audio_temp_path} -vcodec copy -acodec copy {output_path}"
                    else:
                        merge_cmd = f'"{ffmpeg_path}" -i "{video_temp_path}" -c copy "{output_path}"'
                    
                    result = os.system(merge_cmd)
                    
                    if result == 0:
                        console.print("[bold green]视频下载完成![/bold green]")
                                            
                        # 删除临时文件
                        if video_temp_path.exists():
                            video_temp_path.unlink()
                        if audio_temp_path.exists():
                            audio_temp_path.unlink()
                    else:
                        console.print("[bold red]音视频合并失败[/bold red]")
                        
                except Exception as e:
                    console.print(f"[bold red]下载失败: {e}[/bold red]")
                    # 清理临时文件
                    if video_temp_path.exists():
                        video_temp_path.unlink()
                    if audio_temp_path.exists():
                        audio_temp_path.unlink()
                    return
            
            console.print(f"[bold green]视频已保存到: {output_path}[/bold green]")
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            console.print(f"[bold red]下载过程中发生错误: {e}[/bold red]")
            logger.error(f"视频下载失败: {e}\n错误栈:\n{error_traceback}")
    
    run_download()


if __name__ == "__main__":
    cli() 