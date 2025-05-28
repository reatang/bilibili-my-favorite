# 开发指南

本文档面向希望参与项目开发、扩展功能或深入了解项目架构的开发者。

## 项目架构

### 分层架构设计

项目采用现代化的分层架构设计：

1. **核心配置层** (`core/`): 统一管理应用配置、环境变量和全局设置
2. **API路由层** (`api/`): 处理HTTP请求响应、数据验证和路由分发
3. **业务逻辑层** (`services/`): 核心业务逻辑、同步服务、事务处理和状态管理
4. **数据访问层** (`dao/`): 数据库操作抽象、SQL查询和连接管理
5. **数据模型层** (`models/`): 数据结构定义、数据库初始化和迁移脚本
6. **工具层** (`utils/`): 通用功能模块，如日志记录、文件下载等
7. **CLI层** (`cli.py`): 命令行接口，提供完整的管理工具集

### 核心组件详解

#### 数据库连接管理 (`dao/base.py`)
- 单例模式的DatabaseManager
- SQLite WAL模式优化
- 长连接管理和自动清理
- 完整的错误栈追踪

#### 同步服务 (`services/optimized_sync_service.py`)
- 增量同步策略
- 中断恢复机制
- 状态管理和进度追踪
- 删除检测和记录

#### 配置管理 (`core/config.py`)
- 环境变量自动加载
- 路径自动解析
- 类型验证和默认值

## 开发环境搭建

### 1. 环境要求

- Python 3.12+
- uv (推荐) 或 pip
- Git

### 2. 克隆和安装

```bash
git clone <repository-url>
cd bilibili-my-favorite

# 安装依赖
uv sync

# 安装开发依赖
uv add --dev pytest pytest-asyncio black isort mypy
```

### 3. 开发配置

创建开发环境配置文件 `.env.dev`:

```env
# 开发环境配置
DEBUG=true
LOG_LEVEL=DEBUG

# 测试数据库
DATABASE_PATH=./test_bilibili_favorites.db

# B站API凭据
USER_DEDE_USER_ID=your_user_id
USER_SESSDATA=your_sessdata
USER_BILI_JCT=your_bili_jct
USER_BUVID3=your_buvid3
USER_AC_TIME_VALUE=your_ac_time_value
```

### 4. 初始化开发数据库

```bash
python src/cli.py init-db
```

## 代码规范

### 编码标准

- **语言**: 所有注释、文档字符串、日志信息使用中文
- **编码规范**: 遵循PEP 8，使用类型提示
- **命名规范**: 
  - 类名: PascalCase (如 `BilibiliService`)
  - 函数/变量: snake_case (如 `get_video_by_id`)
  - 常量: UPPER_SNAKE_CASE (如 `DATABASE_PATH`)

### 错误处理规范

```python
import traceback
from ..utils.logger import logger

try:
    # 业务逻辑
    result = await some_operation()
except SpecificException as e:
    # 记录详细错误信息
    error_traceback = traceback.format_exc()
    logger.error(f"操作失败: {e}\n错误栈:\n{error_traceback}")
    raise
except Exception as e:
    # 处理未预期的错误
    error_traceback = traceback.format_exc()
    logger.error(f"未预期的错误: {e}\n错误栈:\n{error_traceback}")
    raise
```

### 异步编程规范

- 所有数据库操作使用异步方法
- HTTP请求使用异步客户端
- 服务层方法统一使用 async/await
- 正确处理异步上下文管理器

### 日志规范

```python
from ..utils.logger import logger

# 日志级别使用
logger.debug("调试信息，详细的执行流程")
logger.info("正常操作信息，重要的业务事件")
logger.warning("警告信息，可能的问题但不影响运行")
logger.error("错误信息，需要关注的问题")
```

## 扩展开发

### 添加新API端点

1. **创建路由文件**
   ```python
   # src/bilibili_my_favorite/api/new_feature.py
   from fastapi import APIRouter, HTTPException
   from ..services.new_service import new_service
   from .models import NewFeatureResponse
   
   router = APIRouter(prefix="/api/new-feature", tags=["new-feature"])
   
   @router.get("/", response_model=List[NewFeatureResponse])
   async def get_new_feature():
       """获取新功能数据"""
       try:
           data = await new_service.get_data()
           return data
       except Exception as e:
           logger.error(f"获取新功能数据失败: {e}")
           raise HTTPException(status_code=500, detail="获取数据失败")
   ```

2. **定义数据模型**
   ```python
   # src/bilibili_my_favorite/api/models.py
   class NewFeatureResponse(BaseModel):
       id: int
       name: str
       description: Optional[str] = None
       created_at: datetime
   ```

3. **注册路由**
   ```python
   # src/bilibili_my_favorite/app.py
   from .api.new_feature import router as new_feature_router
   
   app.include_router(new_feature_router)
   ```

### 添加新服务

1. **创建服务类**
   ```python
   # src/bilibili_my_favorite/services/new_service.py
   from ..dao.new_dao import new_dao
   from ..utils.logger import logger
   
   class NewService:
       """新功能服务类"""
       
       async def get_data(self):
           """获取数据"""
           try:
               return await new_dao.get_all()
           except Exception as e:
               logger.error(f"获取数据失败: {e}")
               raise
   
   new_service = NewService()
   ```

2. **创建DAO类**
   ```python
   # src/bilibili_my_favorite/dao/new_dao.py
   from .base import BaseDAO
   
   class NewDAO(BaseDAO):
       """新功能数据访问类"""
       
       async def get_all(self):
           """获取所有数据"""
           query = "SELECT * FROM new_table ORDER BY created_at DESC"
           return await self.fetch_all(query)
   
   new_dao = NewDAO()
   ```

### 数据库迁移

1. **修改表结构**
   ```python
   # src/bilibili_my_favorite/models/database.py
   async def create_new_table(db: aiosqlite.Connection):
       """创建新表"""
       await db.execute("""
           CREATE TABLE IF NOT EXISTS new_table (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT NOT NULL,
               description TEXT,
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )
       """)
   ```

2. **实现迁移脚本**
   ```python
   # src/bilibili_my_favorite/models/database_migration.py
   async def migrate_to_v2(db: aiosqlite.Connection):
       """迁移到版本2"""
       logger.info("开始迁移到版本2...")
       
       # 创建新表
       await create_new_table(db)
       
       # 更新版本号
       await db.execute("UPDATE schema_version SET version = 2")
       await db.commit()
       
       logger.info("迁移到版本2完成")
   ```

### 添加CLI命令

```python
# src/cli.py
@cli.command()
@click.option('--param', help='参数说明')
@async_command
async def new_command(param: str):
    """新命令的说明"""
    try:
        result = await new_service.do_something(param)
        console.print(f"[green]操作成功: {result}[/green]")
    except Exception as e:
        console.print(f"[red]操作失败: {e}[/red]")
        raise click.ClickException(str(e))
```

## 性能优化

### 数据库优化

#### SQLite配置优化
```python
# 在DatabaseManager中的优化配置
PRAGMA_SETTINGS = [
    "PRAGMA journal_mode=WAL",           # WAL模式
    "PRAGMA synchronous=NORMAL",         # 同步模式
    "PRAGMA cache_size=10000",           # 缓存大小
    "PRAGMA temp_store=MEMORY",          # 内存临时存储
    "PRAGMA mmap_size=268435456",        # 内存映射256MB
]
```

#### 查询优化
- 使用索引优化查询性能
- 批量操作减少数据库连接
- 使用事务处理批量更新
- 避免N+1查询问题

### 同步优化

#### 增量同步策略
```python
async def sync_collection_incremental(self, collection_id: str):
    """增量同步收藏夹"""
    # 获取上次同步时间
    last_sync = await self.get_last_sync_time(collection_id)
    
    # 只获取变更的数据
    changed_videos = await self.bilibili_service.get_changed_videos(
        collection_id, since=last_sync
    )
    
    # 处理变更
    for video in changed_videos:
        await self.process_video_change(video)
```

#### 并发控制
- 使用asyncio.Semaphore控制并发数
- 实现请求限流避免被封禁
- 合理设置请求间隔

### Web性能优化

- 使用异步请求处理
- 实现分页查询
- 添加响应缓存
- 优化静态资源加载

## 测试

### 单元测试

```python
# tests/test_services.py
import pytest
from src.bilibili_my_favorite.services.new_service import new_service

@pytest.mark.asyncio
async def test_get_data():
    """测试获取数据"""
    data = await new_service.get_data()
    assert isinstance(data, list)
    assert len(data) >= 0

@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    with pytest.raises(Exception):
        await new_service.invalid_operation()
```

### 集成测试

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from src.bilibili_my_favorite.app import app

client = TestClient(app)

def test_get_collections():
    """测试获取收藏夹API"""
    response = client.get("/api/collections/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_services.py

# 运行测试并生成覆盖率报告
pytest --cov=src/bilibili_my_favorite
```

## 调试

### 日志调试

1. **设置调试级别**
   ```env
   LOG_LEVEL=DEBUG
   ```

2. **查看日志文件**
   ```bash
   tail -f logs/app.log
   ```

3. **使用Rich调试输出**
   ```python
   from rich.console import Console
   console = Console()
   console.print(data, style="bold blue")
   ```

### 数据库调试

```python
# 启用SQL查询日志
import logging
logging.getLogger('aiosqlite').setLevel(logging.DEBUG)
```

### API调试

- 使用FastAPI自动生成的文档: `http://localhost:8000/docs`
- 使用Postman或curl测试API端点
- 检查网络请求和响应

## 部署

### 开发环境部署

```bash
# 启动开发服务器
python src/cli.py serve --reload

# 或使用uvicorn
uvicorn src.bilibili_my_favorite.app:app --reload --host 0.0.0.0 --port 8000
```

### 生产环境部署

```bash
# 使用gunicorn
gunicorn src.bilibili_my_favorite.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 使用Docker
docker build -t bilibili-favorites .
docker run -p 8000:8000 -v $(pwd)/data:/app/data bilibili-favorites
```

### 性能监控

- 使用APM工具监控应用性能
- 设置日志聚合和分析
- 监控数据库性能指标
- 设置告警机制

## 贡献指南

### 提交代码

1. **Fork项目并创建分支**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **编写代码和测试**
   - 遵循代码规范
   - 添加单元测试
   - 更新文档

3. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   git push origin feature/new-feature
   ```

4. **创建Pull Request**
   - 描述变更内容
   - 关联相关Issue
   - 等待代码审查

### 代码审查

- 检查代码质量和规范
- 验证测试覆盖率
- 确认文档更新
- 测试功能正确性

### 发布流程

1. 更新版本号
2. 更新CHANGELOG
3. 运行完整测试
4. 创建发布标签
5. 部署到生产环境

## 常见开发问题

### Q: 如何添加新的数据库表？
A: 
1. 在 `models/database.py` 中定义表结构
2. 在 `models/database_migration.py` 中添加迁移脚本
3. 更新版本号并测试迁移

### Q: 如何处理异步操作中的异常？
A: 使用try-catch块包装异步操作，记录完整错误栈，并适当地重新抛出异常。

### Q: 如何优化数据库查询性能？
A: 
1. 添加适当的索引
2. 使用批量操作
3. 避免N+1查询
4. 使用连接池

### Q: 如何调试同步过程中的问题？
A: 
1. 设置DEBUG日志级别
2. 查看同步上下文状态
3. 检查B站API响应
4. 使用断点调试

## 参考资源

- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [SQLite优化指南](https://www.sqlite.org/optoverview.html)
- [Python异步编程](https://docs.python.org/3/library/asyncio.html)
- [Rich终端库](https://rich.readthedocs.io/)
- [Click CLI框架](https://click.palletsprojects.com/) 