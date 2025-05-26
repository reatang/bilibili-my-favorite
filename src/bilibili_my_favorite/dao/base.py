"""
数据访问层基类
提供通用的数据库操作方法
"""
import aiosqlite
from typing import Optional, Dict, Any, List
from ..core.config import config
from ..utils.logger import logger


class BaseDAO:
    """数据访问层基类"""
    
    def __init__(self):
        self.db_path = config.DATABASE_PATH
    
    async def get_connection(self) -> aiosqlite.Connection:
        """获取数据库连接"""
        db = await aiosqlite.connect(self.db_path)
        db.row_factory = aiosqlite.Row
        return db
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[aiosqlite.Row]:
        """执行查询并返回结果"""
        async with await self.get_connection() as db:
            cursor = await db.execute(query, params)
            return await cursor.fetchall()
    
    async def execute_one(self, query: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
        """执行查询并返回单个结果"""
        async with await self.get_connection() as db:
            cursor = await db.execute(query, params)
            return await cursor.fetchone()
    
    async def execute_insert(self, query: str, params: tuple = ()) -> int:
        """执行插入操作并返回新记录ID"""
        async with await self.get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.lastrowid
    
    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行更新操作并返回影响的行数"""
        async with await self.get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.rowcount
    
    async def execute_delete(self, query: str, params: tuple = ()) -> int:
        """执行删除操作并返回影响的行数"""
        async with await self.get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.rowcount
    
    async def execute_batch(self, query: str, params_list: List[tuple]) -> None:
        """批量执行操作"""
        async with await self.get_connection() as db:
            await db.executemany(query, params_list)
            await db.commit()
    
    def row_to_dict(self, row: Optional[aiosqlite.Row]) -> Optional[Dict[str, Any]]:
        """将数据库行转换为字典"""
        return dict(row) if row else None
    
    def rows_to_dicts(self, rows: List[aiosqlite.Row]) -> List[Dict[str, Any]]:
        """将数据库行列表转换为字典列表"""
        return [dict(row) for row in rows] 