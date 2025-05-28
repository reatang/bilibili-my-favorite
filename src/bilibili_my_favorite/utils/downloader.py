"""
下载工具模块
处理封面图片下载等功能
"""
import asyncio
from pathlib import Path
from typing import Optional
import httpx
from ..core.config import config
from .logger import logger
import os

from bilibili_api import video, Credential, get_client


class CoverDownloader:
    """封面图片下载器"""
    
    def __init__(self):
        self.timeout = config.DOWNLOAD_TIMEOUT
        self.covers_dir = config.COVERS_DIR
        
    async def download_cover(self, bvid: str, cover_url: str) -> Optional[str]:
        """
        下载视频封面图片
        
        Args:
            bvid: 视频BVID
            cover_url: 封面图片URL
            
        Returns:
            本地文件路径，失败时返回None
        """
        if not cover_url or not cover_url.startswith("http"):
            logger.warning(f"无效的封面URL，BVID: {bvid}, URL: {cover_url}")
            return None

        # 确保协议正确
        if cover_url.startswith("//"):
            cover_url = "https:" + cover_url
        
        # 生成本地文件路径
        local_filename = f"{bvid}.jpg"
        local_path = self.covers_dir / local_filename
        
        # 确保目录存在
        self.covers_dir.mkdir(exist_ok=True)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(cover_url, timeout=self.timeout)
                response.raise_for_status()
                
                # 保存文件
                with open(local_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"成功下载封面: BVID {bvid} -> {local_path}")
                return str(local_path)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误下载封面: BVID {bvid}, URL {cover_url}, "
                        f"状态码: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"请求错误下载封面: BVID {bvid}, URL {cover_url}, 错误: {e}")
        except Exception as e:
            logger.error(f"下载封面时发生未知错误: BVID {bvid}, URL {cover_url}, 错误: {e}")
        
        return None
    
    async def batch_download_covers(self, cover_tasks: list[tuple[str, str]], 
                                  max_concurrent: int = 5) -> dict[str, Optional[str]]:
        """
        批量下载封面图片
        
        Args:
            cover_tasks: (bvid, cover_url) 元组列表
            max_concurrent: 最大并发数
            
        Returns:
            {bvid: local_path} 字典
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def download_with_semaphore(bvid: str, cover_url: str):
            async with semaphore:
                result = await self.download_cover(bvid, cover_url)
                results[bvid] = result
                
        tasks = [
            download_with_semaphore(bvid, cover_url) 
            for bvid, cover_url in cover_tasks
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        return results



HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}

class VideoDownloader:
    """视频下载器"""

    def __init__(self):
        self.timeout = config.DOWNLOAD_TIMEOUT
        self.videos_dir = config.VIDEOS_DIR

        if not os.path.exists(self.videos_dir):
            os.makedirs(self.videos_dir)

    async def download_video(self, url: str, out: str, intro: str):
        dwn_id = await get_client().download_create(url, HEADERS)
        bts = 0
        tot = get_client().download_content_length(dwn_id)
        with open(out, "wb") as file:
            while True:
                bts += file.write(await get_client().download_chunk(dwn_id))
                print(f"{intro} - {out} [{bts} / {tot}]", end="\r")
                if bts == tot:
                    break
        print()

# 创建全局下载器实例
cover_downloader = CoverDownloader() 
video_downloader = VideoDownloader()