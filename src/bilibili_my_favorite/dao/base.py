"""
数据访问层基类
提供通用的数据库操作方法
"""
import aiosqlite
import asyncio
import atexit
import signal
import sys
import traceback
from typing import Optional, Dict, Any, List, ClassVar
from ..core.config import config
from ..utils.logger import logger


class DatabaseManager:
    """数据库连接管理器 - 单例模式"""
    
    _instance: Optional['DatabaseManager'] = None
    _connection: Optional[aiosqlite.Connection] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self):
        """初始化数据库连接"""
        if self._initialized:
            return
        
        try:
            self._connection = await aiosqlite.connect(config.DATABASE_PATH)
            self._connection.row_factory = aiosqlite.Row
            
            # 优化SQLite配置
            await self._connection.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式
            await self._connection.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全
            await self._connection.execute("PRAGMA cache_size=10000")  # 增加缓存
            await self._connection.execute("PRAGMA temp_store=MEMORY")  # 临时表存储在内存
            await self._connection.execute("PRAGMA mmap_size=268435456")  # 256MB内存映射
            await self._connection.commit()
            
            self._initialized = True
            logger.info("数据库连接已初始化，启用WAL模式和性能优化")
            
            # 注册清理函数
            atexit.register(self._cleanup_sync)
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def close(self):
        """关闭数据库连接"""
        if self._connection:
            try:
                await self._connection.close()
                logger.info("数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭数据库连接时出错: {e}")
            finally:
                self._connection = None
                self._initialized = False
    
    def _cleanup_sync(self):
        """同步清理函数（用于atexit）"""
        if self._connection:
            try:
                # 在事件循环中运行异步清理
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务
                    loop.create_task(self.close())
                else:
                    # 如果事件循环已停止，直接运行
                    loop.run_until_complete(self.close())
            except Exception as e:
                logger.error(f"清理数据库连接时出错: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，正在清理资源...")
        self._cleanup_sync()
        sys.exit(0)
    
    @property
    def connection(self) -> aiosqlite.Connection:
        """获取数据库连接"""
        if not self._initialized or not self._connection:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        return self._connection


class BaseDAO:
    """数据访问层基类"""
    
    # 类级别的数据库管理器
    _db_manager: ClassVar[DatabaseManager] = DatabaseManager()
    
    def __init__(self):
        self.db_path = config.DATABASE_PATH
    
    @classmethod
    async def initialize_database(cls):
        """初始化数据库连接（应用启动时调用）"""
        await cls._db_manager.initialize()
    
    @classmethod
    async def close_database(cls):
        """关闭数据库连接（应用关闭时调用）"""
        await cls._db_manager.close()
    
    @property
    def db(self) -> aiosqlite.Connection:
        """获取数据库连接"""
        return self._db_manager.connection
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[aiosqlite.Row]:
        """执行查询并返回结果"""
        try:
            cursor = await self.db.execute(query, params)
            return await cursor.fetchall()
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"执行查询失败: {query}, 参数: {params}, 错误: {e}\n错误栈:\n{error_traceback}")
            raise
    
    async def execute_one(self, query: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
        """执行查询并返回单个结果"""
        try:
            cursor = await self.db.execute(query, params)
            return await cursor.fetchone()
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"执行单条查询失败: {query}, 参数: {params}, 错误: {e}\n错误栈:\n{error_traceback}")
            raise
    
    async def execute_insert(self, query: str, params: tuple = ()) -> int:
        """执行插入操作并返回新记录ID"""
        try:
            cursor = await self.db.execute(query, params)
            await self.db.commit()
            return cursor.lastrowid
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"执行插入失败: {query}, 参数: {params}, 错误: {e}\n错误栈:\n{error_traceback}")
            await self.db.rollback()
            raise
    
    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行更新操作并返回影响的行数"""
        try:
            cursor = await self.db.execute(query, params)
            await self.db.commit()
            return cursor.rowcount
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"执行更新失败: {query}, 参数: {params}, 错误: {e}\n错误栈:\n{error_traceback}")
            await self.db.rollback()
            raise
    
    async def execute_delete(self, query: str, params: tuple = ()) -> int:
        """执行删除操作并返回影响的行数"""
        try:
            cursor = await self.db.execute(query, params)
            await self.db.commit()
            return cursor.rowcount
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"执行删除失败: {query}, 参数: {params}, 错误: {e}\n错误栈:\n{error_traceback}")
            await self.db.rollback()
            raise
    
    async def execute_batch(self, query: str, params_list: List[tuple]) -> None:
        """批量执行操作"""
        try:
            await self.db.executemany(query, params_list)
            await self.db.commit()
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"批量执行失败: {query}, 错误: {e}\n错误栈:\n{error_traceback}")
            await self.db.rollback()
            raise
    
    async def execute_transaction(self, operations: List[tuple]) -> None:
        """执行事务操作
        
        Args:
            operations: 操作列表，每个元素为 (query, params) 元组
        """
        try:
            for query, params in operations:
                await self.db.execute(query, params)
            await self.db.commit()
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"事务执行失败: {e}\n错误栈:\n{error_traceback}")
            await self.db.rollback()
            raise
    
    def row_to_dict(self, row: Optional[aiosqlite.Row]) -> Optional[Dict[str, Any]]:
        """将数据库行转换为字典"""
        return dict(row) if row else None
    
    def rows_to_dicts(self, rows: List[aiosqlite.Row]) -> List[Dict[str, Any]]:
        """将数据库行列表转换为字典列表"""
        return [dict(row) for row in rows] 