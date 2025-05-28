"""
同步上下文管理器
管理同步任务的状态、锁文件和数据缓存
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from ..core.config import config
from ..utils.logger import logger


class SyncContext:
    """同步上下文管理器"""
    
    def __init__(self, task_id: str = None):
        self.task_id = task_id or str(uuid.uuid4())
        self.lock_file_path = Path(config.DATA_DIR) / "sync_lock.json"
        self.data_dir = Path(config.DATA_DIR) / f"sync_data_{self.task_id}"
        
        # 同步状态
        self.status = "initializing"  # initializing, fetching, processing, completed, failed
        self.collections_to_process: List[Dict[str, Any]] = []
        self.current_collection: Optional[Dict[str, Any]] = None
        self.current_page = 1
        self.processed_collections: List[str] = []
        self.failed_collections: List[Dict[str, Any]] = []
        
        # 统计信息
        self.stats = {
            "collections_processed": 0,
            "videos_added": 0,
            "videos_updated": 0,
            "videos_deleted": 0,
            "covers_downloaded": 0,
            "errors": [],
            "deleted_videos": []  # 记录被删除的视频详情
        }
        
        # 时间戳
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        
    def save_lock_file(self):
        """保存锁文件"""
        try:
            # 确保目录存在
            self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            lock_data = {
                "task_id": self.task_id,
                "status": self.status,
                "collections_to_process": self.collections_to_process,
                "current_collection": self.current_collection,
                "current_page": self.current_page,
                "processed_collections": self.processed_collections,
                "failed_collections": self.failed_collections,
                "stats": self.stats,
                "created_at": self.created_at,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.lock_file_path, 'w', encoding='utf-8') as f:
                json.dump(lock_data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"锁文件已保存: {self.lock_file_path}")
            
        except Exception as e:
            logger.error(f"保存锁文件失败: {e}")
            raise
    
    @classmethod
    def load_from_lock_file(cls, lock_file_path: str) -> 'SyncContext':
        """从锁文件加载同步上下文"""
        try:
            with open(lock_file_path, 'r', encoding='utf-8') as f:
                lock_data = json.load(f)
            
            context = cls(task_id=lock_data["task_id"])
            context.status = lock_data["status"]
            context.collections_to_process = lock_data["collections_to_process"]
            context.current_collection = lock_data["current_collection"]
            context.current_page = lock_data["current_page"]
            context.processed_collections = lock_data["processed_collections"]
            context.failed_collections = lock_data["failed_collections"]
            context.stats = lock_data["stats"]
            context.created_at = lock_data["created_at"]
            context.updated_at = lock_data["updated_at"]
            
            logger.info(f"从锁文件加载同步上下文: {lock_file_path}")
            return context
            
        except Exception as e:
            logger.error(f"加载锁文件失败: {e}")
            raise
    
    @classmethod
    def find_existing_lock_file(cls) -> str:
        """查找现有的锁文件"""
        try:
            lock_file = Path(config.DATA_DIR) / "sync_lock.json"
            if lock_file.exists():
                return str(lock_file)
            return ""
            
        except Exception as e:
            logger.error(f"查找锁文件失败: {e}")
            return ""
    
    def save_collection_page_data(self, collection_id: str, page: int, data: List[Dict[str, Any]]):
        """保存收藏夹分页数据到文件"""
        try:
            # 确保数据目录存在
            collection_dir = self.data_dir / collection_id
            collection_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存分页数据
            page_file = collection_dir / f"page_{page}.json"
            with open(page_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存收藏夹 {collection_id} 第 {page} 页数据: {len(data)} 个视频")
            
        except Exception as e:
            logger.error(f"保存分页数据失败: {e}")
            raise
    
    def load_collection_page_data(self, collection_id: str, page: int) -> Optional[List[Dict[str, Any]]]:
        """加载收藏夹分页数据"""
        try:
            page_file = self.data_dir / collection_id / f"page_{page}.json"
            if not page_file.exists():
                return None
            
            with open(page_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"加载收藏夹 {collection_id} 第 {page} 页数据: {len(data)} 个视频")
            return data
            
        except Exception as e:
            logger.error(f"加载分页数据失败: {e}")
            return None
    
    def get_collection_all_pages(self, collection_id: str) -> List[List[Dict[str, Any]]]:
        """获取收藏夹的所有分页数据"""
        try:
            collection_dir = self.data_dir / collection_id
            if not collection_dir.exists():
                return []
            
            all_pages = []
            page = 1
            
            while True:
                page_data = self.load_collection_page_data(collection_id, page)
                if page_data is None:
                    break
                all_pages.append(page_data)
                page += 1
            
            logger.debug(f"收藏夹 {collection_id} 共有 {len(all_pages)} 页数据")
            return all_pages
            
        except Exception as e:
            logger.error(f"获取收藏夹所有分页数据失败: {e}")
            return []
    
    def get_collection_all_videos(self, collection_id: str) -> List[Dict[str, Any]]:
        """获取收藏夹的所有视频数据"""
        all_pages = self.get_collection_all_pages(collection_id)
        all_videos = []
        
        for page_data in all_pages:
            all_videos.extend(page_data)
        
        logger.debug(f"收藏夹 {collection_id} 共有 {len(all_videos)} 个视频")
        return all_videos
    
    def update_status(self, status: str):
        """更新同步状态"""
        self.status = status
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.save_lock_file()
        logger.info(f"同步状态更新为: {status}")
    
    def set_current_collection(self, collection: Dict[str, Any], page: int = 1):
        """设置当前处理的收藏夹"""
        self.current_collection = collection
        self.current_page = page
        self.save_lock_file()
        logger.info(f"开始处理收藏夹: {collection.get('title', 'Unknown')} (ID: {collection.get('id')})")
    
    def mark_collection_completed(self, collection_id: str):
        """标记收藏夹处理完成"""
        if collection_id not in self.processed_collections:
            self.processed_collections.append(collection_id)
        
        # 从待处理列表中移除
        self.collections_to_process = [
            c for c in self.collections_to_process 
            if str(c.get('id')) != str(collection_id)
        ]
        
        self.current_collection = None
        self.current_page = 1
        self.stats["collections_processed"] += 1
        self.save_lock_file()
        
        logger.info(f"收藏夹 {collection_id} 处理完成")
    
    def mark_collection_failed(self, collection: Dict[str, Any], error: str):
        """标记收藏夹处理失败"""
        failed_info = {
            "collection": collection,
            "error": error,
            "failed_at": datetime.now(timezone.utc).isoformat()
        }
        self.failed_collections.append(failed_info)
        self.stats["errors"].append(f"收藏夹 {collection.get('title', 'Unknown')}: {error}")
        
        # 从待处理列表中移除
        collection_id = str(collection.get('id'))
        self.collections_to_process = [
            c for c in self.collections_to_process 
            if str(c.get('id')) != collection_id
        ]
        
        self.save_lock_file()
        logger.error(f"收藏夹 {collection.get('title', 'Unknown')} 处理失败: {error}")
    
    def cleanup(self):
        """清理锁文件（保留数据目录作为历史记录）"""
        try:
            # 删除锁文件
            if self.lock_file_path.exists():
                self.lock_file_path.unlink()
                logger.info(f"删除锁文件: {self.lock_file_path}")
            
            # 保留数据目录作为历史记录
            logger.info(f"保留数据目录作为历史记录: {self.data_dir}")
                
        except Exception as e:
            logger.error(f"清理锁文件失败: {e}")
    
    def is_resumable(self) -> bool:
        """检查是否可以恢复同步"""
        return (
            self.status in ["fetching", "processing"] and
            (self.collections_to_process or self.current_collection)
        )
    
    def get_progress_info(self) -> Dict[str, Any]:
        """获取进度信息"""
        total_collections = len(self.processed_collections) + len(self.collections_to_process)
        if self.current_collection:
            total_collections += 1
        
        return {
            "task_id": self.task_id,
            "status": self.status,
            "total_collections": total_collections,
            "processed_collections": len(self.processed_collections),
            "remaining_collections": len(self.collections_to_process),
            "current_collection": self.current_collection.get('title') if self.current_collection else None,
            "current_page": self.current_page,
            "stats": self.stats,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        } 