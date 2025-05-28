"""
B站API服务
处理与B站API的交互逻辑
"""
import asyncio
import random
from typing import List, Dict, Any, Optional
from ..core.config import config
from ..core.credential import SuperCredential
from ..utils.logger import logger

from bilibili_api import favorite_list, video



class BilibiliService:
    """B站API服务类"""
    
    def __init__(self):
        self.credential = None
        self._initialized = False
    
    def _setup_client(self):
        """设置B站API客户端"""
        if self._initialized:
            return
            
        try:
            from bilibili_api import Credential, select_client, request_settings
            
            select_client("curl_cffi")
            request_settings.set("impersonate", "chrome136")
            
            if config.validate_bilibili_credentials():
                if config.RAW_COOKIES is not None and len(config.RAW_COOKIES) > 0:
                    self.credential = SuperCredential.from_raw_cookies(config.RAW_COOKIES, config.USER_AC_TIME_VALUE)
                else:
                    self.credential = Credential(
                        sessdata=config.USER_SESSDATA,
                        bili_jct=config.USER_BILI_JCT,
                        buvid3=config.USER_BUVID3,
                        ac_time_value=config.USER_AC_TIME_VALUE,
                        dedeuserid=config.USER_DEDE_USER_ID,
                )
                logger.info("B站API凭据初始化成功")
            else:
                logger.error("B站API凭据不完整，无法初始化")
                
            self._initialized = True
        except Exception as e:
            logger.error(f"初始化B站API客户端失败: {e}")
            raise
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        if not self._initialized:
            self._setup_client()
        return self.credential is not None
    
    async def get_favorite_lists(self, uid: str = None) -> List[Dict[str, Any]]:
        """
        获取用户的收藏夹列表
        
        Args:
            uid: 用户ID，默认使用配置中的用户ID
            
        Returns:
            收藏夹列表
        """
        if not self.is_authenticated():
            raise ValueError("未设置B站API凭据")
        
        uid = uid or config.USER_DEDE_USER_ID
        if not uid:
            raise ValueError("未设置用户ID")
        
        try:
            response = await favorite_list.get_video_favorite_list(
                uid=uid, credential=self.credential
            )

            if not response or not response.get("list"):
                logger.warning("未获取到收藏夹列表或列表为空")
                return []
            
            collections = response["list"]
            logger.info(f"成功获取到 {len(collections)} 个收藏夹")
            return collections
            
        except Exception as e:
            logger.error(f"获取收藏夹列表失败: {e}")
            raise
    
    async def get_favorite_videos(self, favorite_id: int, 
                                max_pages: int = None) -> List[Dict[str, Any]]:
        """
        获取收藏夹中的所有视频
        
        Args:
            favorite_id: 收藏夹ID
            max_pages: 最大页数限制
            
        Returns:
            视频列表
        """
        if not self.is_authenticated():
            raise ValueError("未设置B站API凭据")
        
        max_pages = max_pages or config.MAX_PAGES_PER_COLLECTION
        all_videos = []
        page = 1
        has_more = True
        
        logger.info(f"开始获取收藏夹 {favorite_id} 的视频列表")
        
        while has_more and page <= max_pages:
            try:
                from bilibili_api import favorite_list
                
                result = await favorite_list.get_video_favorite_list_content(
                    media_id=favorite_id, page=page, credential=self.credential
                )
                
                if not result.get("medias"):
                    logger.info(f"收藏夹 {favorite_id} 第 {page} 页无更多视频")
                    break
                
                videos = result["medias"]
                all_videos.extend(videos)
                
                logger.info(f"收藏夹 {favorite_id} 第 {page} 页获取到 {len(videos)} 个视频，"
                          f"总计: {len(all_videos)}")
                
                has_more = result.get("has_more", False)
                page += 1
                
                # 添加请求延迟
                if has_more and page <= max_pages:
                    await asyncio.sleep(random.randint(config.REQUEST_DELAY, config.REQUEST_DELAY *6) / 1000)
                    
            except Exception as e:
                logger.error(f"获取收藏夹 {favorite_id} 第 {page} 页失败: {e}")
                break
        
        if page > max_pages:
            logger.warning(f"收藏夹 {favorite_id} 超过最大页数限制 {max_pages}，停止获取")
        
        logger.info(f"收藏夹 {favorite_id} 共获取到 {len(all_videos)} 个视频")
        return all_videos
    
    async def get_video_info(self, bvid: str) -> Optional[Dict[str, Any]]:
        """
        获取单个视频信息
        
        Args:
            bvid: 视频BVID
            
        Returns:
            视频信息字典
        """
        if not self.is_authenticated():
            raise ValueError("未设置B站API凭据")
        
        try:
            # 这里可以添加获取单个视频详细信息的逻辑
            v = video.Video(bvid=bvid)
            logger.info(f"获取视频 {bvid} 的详细信息")
            video_info = await v.get_info()
            return video_info
            
        except Exception as e:
            logger.error(f"获取视频 {bvid} 信息失败: {e}")
            return None
    
    async def batch_get_favorite_videos(self, favorite_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        """
        批量获取多个收藏夹的视频
        
        Args:
            favorite_ids: 收藏夹ID列表
            
        Returns:
            {favorite_id: videos} 字典
        """
        results = {}
        
        for favorite_id in favorite_ids:
            try:
                videos = await self.get_favorite_videos(favorite_id)
                results[favorite_id] = videos
                
                # 添加收藏夹间的延迟
                if favorite_id != favorite_ids[-1]:
                    await asyncio.sleep(random.randint(config.REQUEST_DELAY, config.REQUEST_DELAY *6) / 1000)
                    
            except Exception as e:
                logger.error(f"批量获取收藏夹 {favorite_id} 失败: {e}")
                results[favorite_id] = []
        
        return results


# # 创建全局服务实例
bilibili_service = BilibiliService() 