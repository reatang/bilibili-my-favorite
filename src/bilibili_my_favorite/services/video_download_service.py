"""
视频下载服务
处理B站视频下载的核心逻辑
"""
import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
import traceback

from bilibili_api import video
from ..core.bilibili_plus import get_download_url
from ..models.task_models import BaseTask, TaskResult, VideoDownloadTask
from ..models.types import (
    BilibiliVideoInfoDict, VideoDownloadInfoDict, DownloadStreamDict, 
    VideoInfoDict, VideoPageDict
)
from ..services.bilibili_service import bilibili_service
from ..utils.downloader import video_downloader
from ..utils.encoding import safe_subprocess_run
from ..utils.logger import logger
from ..core.config import config


class VideoDownloadService:
    """视频下载服务"""
    
    def __init__(self):
        self.bilibili_service = bilibili_service
        self.video_downloader = video_downloader
    
    async def execute_download_task(self, task: BaseTask) -> TaskResult:
        """执行视频下载任务"""
        if not isinstance(task, VideoDownloadTask):
            # 如果不是VideoDownloadTask类型，从parameters中提取参数
            bvid = task.parameters.get("bvid")
            page = task.parameters.get("page", 0)
            quality = task.parameters.get("quality", 80)
            output_filename = task.parameters.get("output_filename")
            ffmpeg_path = task.parameters.get("ffmpeg_path", "ffmpeg")
        else:
            bvid = task.parameters["bvid"]
            page = task.parameters["page"]
            quality = task.parameters["quality"]
            output_filename = task.parameters["output_filename"]
            ffmpeg_path = task.parameters["ffmpeg_path"]
        
        try:
            # 检查B站凭据
            if not self.bilibili_service.is_authenticated():
                return TaskResult(
                    success=False,
                    error_message="B站API凭据不完整",
                    error_code="AUTH_ERROR"
                )
            
            # 检查FFmpeg
            if not self._check_ffmpeg(ffmpeg_path):
                return TaskResult(
                    success=False,
                    error_message=f"FFmpeg不可用: {ffmpeg_path}",
                    error_code="FFMPEG_ERROR"
                )
            
            # 获取视频信息
            video_info = await self._get_video_info(bvid)
            if not video_info:
                return TaskResult(
                    success=False,
                    error_message="获取视频信息失败",
                    error_code="VIDEO_INFO_ERROR"
                )
            
            # 检查分P索引
            if page >= len(video_info['pages']):
                return TaskResult(
                    success=False,
                    error_message=f"分P索引 {page} 超出范围（0-{len(video_info['pages'])-1}）",
                    error_code="PAGE_INDEX_ERROR"
                )
            
            page_info = video_info['pages'][page]
            cid = page_info['cid']
            
            # 获取下载链接
            download_streams = await self._get_download_streams(bvid, cid, quality)
            if not download_streams:
                return TaskResult(
                    success=False,
                    error_message="获取下载链接失败",
                    error_code="DOWNLOAD_URL_ERROR"
                )
            
            # 生成输出文件名和路径
            if not output_filename:
                output_filename = self._generate_output_filename(video_info, page)
            
            output_path = config.VIDEOS_DIR / f"{output_filename}.mp4"
            
            # 执行下载
            success = await self._download_video_streams(download_streams, output_path, ffmpeg_path)
            
            if success:
                return TaskResult(
                    success=True,
                    data={
                        "video_info": {
                            "title": video_info["title"],
                            "uploader": video_info["owner"]["name"],
                            "duration": video_info["duration"],
                            "page": page + 1,
                            "page_title": page_info["part"]
                        }
                    },
                    output_files=[str(output_path)],
                    statistics={
                        "file_size": output_path.stat().st_size if output_path.exists() else 0,
                        "quality": quality
                    }
                )
            else:
                return TaskResult(
                    success=False,
                    error_message="视频下载失败",
                    error_code="DOWNLOAD_ERROR"
                )
                
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"视频下载失败: {e}\n{error_traceback}")
            return TaskResult(
                success=False,
                error_message=str(e),
                error_code="UNKNOWN_ERROR"
            )
    
    def _check_ffmpeg(self, ffmpeg_path: str) -> bool:
        """检查FFmpeg是否可用"""
        try:
            result = safe_subprocess_run(
                [ffmpeg_path, '-version'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def _get_video_info(self, bvid: str) -> Optional[BilibiliVideoInfoDict]:
        """获取视频信息"""
        try:
            credential = self.bilibili_service.credential
            v = video.Video(bvid=bvid, credential=credential)
            info = await v.get_info()
            return info
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return None
    
    async def _get_download_streams(self, bvid: str, cid: int, quality: int) -> Optional[DownloadStreamDict]:
        """获取下载流信息"""
        try:
            credential = self.bilibili_service.credential
            
            # 获取下载链接
            download_url_data = await get_download_url(
                bvid=bvid, cid=cid, credential=credential, qn=quality
            )
            
            # 解析下载信息
            detecter = video.VideoDownloadURLDataDetecter(data=download_url_data)
            streams = detecter.detect_best_streams()
            
            if not streams:
                logger.error("未找到可用的视频流")
                return None
            
            return DownloadStreamDict(
                streams=streams,
                detecter=detecter,
                download_data=download_url_data
            )
            
        except Exception as e:
            logger.error(f"获取下载流失败: {e}")
            return None
    
    def _generate_output_filename(self, video_info: BilibiliVideoInfoDict, page: int) -> str:
        """生成输出文件名"""
        # 清理文件名中的非法字符
        safe_title = "".join(
            c for c in video_info['title'] 
            if c.isalnum() or c in (' ', '-', '_', '.')
        ).strip()
        
        # 限制文件名长度
        if len(safe_title) > 100:
            safe_title = safe_title[:100]
        
        bvid = video_info.get('bvid', 'unknown')
        return f"{bvid}_{safe_title}_P{page+1}"
    
    async def _download_video_streams(self, stream_info: DownloadStreamDict, 
                                    output_path: Path, ffmpeg_path: str) -> bool:
        """下载视频流"""
        try:
            streams = stream_info["streams"]
            detecter = stream_info["detecter"]
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if detecter.check_flv_mp4_stream():
                # FLV流下载
                return await self._download_flv_stream(streams[0], output_path, ffmpeg_path)
            else:
                # MP4流下载（分离的视频和音频流）
                return await self._download_mp4_streams(streams, output_path, ffmpeg_path)
                
        except Exception as e:
            logger.error(f"下载视频流失败: {e}")
            return False
    
    async def _download_flv_stream(self, stream: Any, output_path: Path, ffmpeg_path: str) -> bool:
        """下载FLV流并转换"""
        temp_file_path = output_path.parent / f"{output_path.stem}.temp.flv"
        
        try:
            logger.info(f"下载FLV流: {stream.url}")
            
            # 下载FLV文件
            await self.video_downloader.download_video(
                stream.url, str(temp_file_path), "下载FLV音视频流"
            )
            
            # 转换格式
            logger.info("转换视频格式...")
            convert_cmd = [
                ffmpeg_path, 
                "-i", str(temp_file_path), 
                "-c", "copy", 
                str(output_path),
                "-y"  # 覆盖输出文件
            ]
            
            result = safe_subprocess_run(convert_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"视频下载完成: {output_path}")
                return True
            else:
                logger.error(f"视频格式转换失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"FLV流下载失败: {e}")
            return False
        finally:
            # 删除临时文件
            if temp_file_path.exists():
                temp_file_path.unlink()
    
    async def _download_mp4_streams(self, streams: List[Any], output_path: Path, ffmpeg_path: str) -> bool:
        """下载分离的MP4流并合并"""
        video_temp_path = output_path.parent / f"{output_path.stem}.video_temp.m4s"
        audio_temp_path = output_path.parent / f"{output_path.stem}.audio_temp.m4s"
        
        try:
            logger.info("下载分离的视频/音频流...")
            
            # 下载视频流
            if not video_temp_path.exists():
                logger.info(f"下载视频流: {streams[0].url}")
                await self.video_downloader.download_video(
                    streams[0].url, str(video_temp_path), "下载视频流"
                )
            
            # 下载音频流（如果存在）
            if len(streams) > 1:
                if not audio_temp_path.exists():
                    logger.info(f"下载音频流: {streams[1].url}")
                    await self.video_downloader.download_video(
                        streams[1].url, str(audio_temp_path), "下载音频流"
                    )
            
            # 合并音视频
            logger.info("合并音视频流...")
            if len(streams) > 1:
                merge_cmd = [
                    ffmpeg_path,
                    "-i", str(video_temp_path),
                    "-i", str(audio_temp_path),
                    "-vcodec", "copy",
                    "-acodec", "copy",
                    str(output_path),
                    "-y"  # 覆盖输出文件
                ]
            else:
                merge_cmd = [
                    ffmpeg_path,
                    "-i", str(video_temp_path),
                    "-c", "copy",
                    str(output_path),
                    "-y"
                ]
            
            result = safe_subprocess_run(merge_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"视频下载完成: {output_path}")
                return True
            else:
                logger.error(f"音视频合并失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"MP4流下载失败: {e}")
            return False
        finally:
            # 清理临时文件
            if video_temp_path.exists():
                video_temp_path.unlink()
            if audio_temp_path.exists():
                audio_temp_path.unlink()
    
    # =============================================================================
    # 便捷方法
    # =============================================================================
    
    async def download_video_simple(self, bvid: str, page: int = 0, quality: int = 80, 
                                  output_filename: Optional[str] = None) -> TaskResult:
        """简单的视频下载方法（不通过任务系统）"""
        task = VideoDownloadTask(
            bvid=bvid,
            page=page,
            quality=quality,
            output_filename=output_filename
        )
        
        return await self.execute_download_task(task)
    
    async def get_video_download_info(self, bvid: str, page: int = 0) -> Optional[VideoDownloadInfoDict]:
        """获取视频下载信息（不执行下载）"""
        try:
            # 获取视频信息
            video_info = await self._get_video_info(bvid)
            if not video_info:
                return None
            
            # 检查分P索引
            if page >= len(video_info['pages']):
                return None
            
            page_info = video_info['pages'][page]
            
            return VideoDownloadInfoDict(
                bvid=bvid,
                title=video_info["title"],
                uploader=video_info["owner"]["name"],
                duration=video_info["duration"],
                pages=len(video_info['pages']),
                current_page={
                    "index": page,
                    "title": page_info["part"],
                    "cid": page_info["cid"]
                },
                available_qualities=[16, 32, 64, 80, 112]  # 常见质量选项
            )
            
        except Exception as e:
            logger.error(f"获取视频下载信息失败: {e}")
            return None 