"""
任务数据访问层
处理任务的数据库操作
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from .base import BaseDAO
from ..models.task_models import BaseTask, TaskStatus, TaskType
from ..utils.logger import logger


class TaskDAO(BaseDAO):
    """任务数据访问对象"""
    
    async def table_exists(self) -> bool:
        """检查任务表是否存在"""
        try:
            query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='tasks'
            """
            rows = await self.execute_query(query)
            return len(rows) > 0
        except Exception as e:
            logger.error(f"检查任务表是否存在失败: {e}")
            return False

    async def create_task_table(self):
        """创建任务表"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            progress_data TEXT DEFAULT '{}',
            result_data TEXT DEFAULT NULL,
            parameters TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            started_at TEXT DEFAULT NULL,
            completed_at TEXT DEFAULT NULL,
            updated_at TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            retry_count INTEGER DEFAULT 0,
            timeout INTEGER DEFAULT NULL
        )
        """
        await self.execute_query(create_sql)
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC)",
        ]
        
        for index_sql in indexes:
            await self.execute_query(index_sql)
        
        logger.info("任务表创建完成")
    
    async def save_task(self, task: BaseTask) -> bool:
        """保存任务"""
        # 检查表是否存在
        if not await self.table_exists():
            logger.error("任务表不存在，请先运行 'python -m src.cli init-db' 初始化数据库")
            return False
        
        try:
            # 准备数据
            progress_json = json.dumps({
                "current": task.progress.current,
                "total": task.progress.total,
                "percentage": task.progress.percentage,
                "message": task.progress.message,
                "sub_tasks": task.progress.sub_tasks
            }, ensure_ascii=False)
            
            result_json = None
            if task.result:
                result_json = json.dumps({
                    "success": task.result.success,
                    "data": task.result.data,
                    "error_message": task.result.error_message,
                    "error_code": task.result.error_code,
                    "output_files": task.result.output_files,
                    "statistics": task.result.statistics
                }, ensure_ascii=False)
            
            parameters_json = json.dumps(task.parameters, ensure_ascii=False)
            
            # 检查任务是否已存在
            existing = await self.get_task_by_id(task.task_id)
            
            if existing:
                # 更新现有任务
                update_sql = """
                UPDATE tasks SET
                    task_type = ?, title = ?, description = ?, status = ?,
                    progress_data = ?, result_data = ?, parameters = ?,
                    started_at = ?, completed_at = ?, updated_at = ?,
                    priority = ?, max_retries = ?, retry_count = ?, timeout = ?
                WHERE task_id = ?
                """
                await self.execute_update(update_sql, (
                    task.task_type.value,
                    task.title,
                    task.description,
                    task.status.value,
                    progress_json,
                    result_json,
                    parameters_json,
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    datetime.now().isoformat(),
                    task.priority,
                    task.max_retries,
                    task.retry_count,
                    task.timeout,
                    task.task_id
                ))
            else:
                # 插入新任务
                insert_sql = """
                INSERT INTO tasks (
                    task_id, task_type, title, description, status,
                    progress_data, result_data, parameters,
                    created_at, started_at, completed_at, updated_at,
                    priority, max_retries, retry_count, timeout
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                await self.execute_insert(insert_sql, (
                    task.task_id,
                    task.task_type.value,
                    task.title,
                    task.description,
                    task.status.value,
                    progress_json,
                    result_json,
                    parameters_json,
                    task.created_at.isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    datetime.now().isoformat(),
                    task.priority,
                    task.max_retries,
                    task.retry_count,
                    task.timeout
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"保存任务失败: {e}")
            return False
    
    async def get_task_by_id(self, task_id: str) -> Optional[BaseTask]:
        """根据ID获取任务"""
        try:
            query = "SELECT * FROM tasks WHERE task_id = ?"
            rows = await self.execute_query(query, (task_id,))
            
            if not rows:
                return None
            
            return self._row_to_task(rows[0])
            
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return None
    
    async def get_tasks_by_status(self, status: TaskStatus, limit: int = 100) -> List[BaseTask]:
        """根据状态获取任务列表"""
        try:
            query = """
            SELECT * FROM tasks 
            WHERE status = ? 
            ORDER BY priority DESC, created_at ASC 
            LIMIT ?
            """
            rows = await self.execute_query(query, (status.value, limit))
            
            return [self._row_to_task(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            return []
    
    async def get_tasks_by_type(self, task_type: TaskType, limit: int = 100) -> List[BaseTask]:
        """根据类型获取任务列表"""
        try:
            query = """
            SELECT * FROM tasks 
            WHERE task_type = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """
            rows = await self.execute_query(query, (task_type.value, limit))
            
            return [self._row_to_task(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            return []
    
    async def get_active_tasks(self) -> List[BaseTask]:
        """获取活跃任务（运行中或等待中）"""
        try:
            query = """
            SELECT * FROM tasks 
            WHERE status IN ('pending', 'running', 'paused')
            ORDER BY priority DESC, created_at ASC
            """
            rows = await self.execute_query(query)
            
            return [self._row_to_task(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取活跃任务失败: {e}")
            return []
    
    async def get_recent_tasks(self, limit: int = 50) -> List[BaseTask]:
        """获取最近的任务"""
        try:
            query = """
            SELECT * FROM tasks 
            ORDER BY updated_at DESC 
            LIMIT ?
            """
            rows = await self.execute_query(query, (limit,))
            
            return [self._row_to_task(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取最近任务失败: {e}")
            return []
    
    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            query = "DELETE FROM tasks WHERE task_id = ?"
            await self.execute_query(query, (task_id,))
            return True
            
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return False
    
    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """清理旧任务"""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            query = """
            DELETE FROM tasks 
            WHERE status IN ('completed', 'failed', 'cancelled') 
            AND completed_at < ?
            """
            
            cursor = await self.execute_query(query, (cutoff_date,))
            deleted_count = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
            
            logger.info(f"清理了 {deleted_count} 个旧任务")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧任务失败: {e}")
            return 0
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        try:
            # 按状态统计
            status_query = """
            SELECT status, COUNT(*) as count 
            FROM tasks 
            GROUP BY status
            """
            status_rows = await self.execute_query(status_query)
            status_stats = {row[0]: row[1] for row in status_rows}
            
            # 按类型统计
            type_query = """
            SELECT task_type, COUNT(*) as count 
            FROM tasks 
            GROUP BY task_type
            """
            type_rows = await self.execute_query(type_query)
            type_stats = {row[0]: row[1] for row in type_rows}
            
            # 今日任务统计
            today = datetime.now().date().isoformat()
            today_query = """
            SELECT COUNT(*) 
            FROM tasks 
            WHERE DATE(created_at) = ?
            """
            today_rows = await self.execute_query(today_query, (today,))
            today_count = today_rows[0][0] if today_rows else 0
            
            return {
                "status_distribution": status_stats,
                "type_distribution": type_stats,
                "today_tasks": today_count,
                "total_tasks": sum(status_stats.values())
            }
            
        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}
    
    def _row_to_task(self, row) -> BaseTask:
        """将数据库行转换为任务对象"""
        # 解析进度数据
        progress_data = json.loads(row[5]) if row[5] else {}
        
        # 解析结果数据
        result_data = json.loads(row[6]) if row[6] else None
        
        # 解析参数数据
        parameters = json.loads(row[7]) if row[7] else {}
        
        # 创建任务对象
        task_dict = {
            "task_id": row[0],
            "task_type": row[1],
            "title": row[2],
            "description": row[3],
            "status": row[4],
            "progress": progress_data,
            "result": result_data,
            "parameters": parameters,
            "created_at": row[8],
            "started_at": row[9],
            "completed_at": row[10],
            "updated_at": row[11],
            "priority": row[12],
            "max_retries": row[13],
            "retry_count": row[14],
            "timeout": row[15]
        }
        
        return BaseTask.from_dict(task_dict)


# 创建全局实例
task_dao = TaskDAO() 