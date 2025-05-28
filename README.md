# B站收藏夹本地同步管理系统

一个用于本地同步和管理B站收藏夹的现代化Web应用系统，支持视频信息同步、封面下载、删除检测、官方影视作品识别等功能。

**注意事项**：使用此模块时请仅用于学习和测试，禁止用于非法用途及其他恶劣的社区行为如：恶意刷屏、辱骂黄暴、各种形式的滥用等，违规此模块许可证 GNU General Public License Version 3 及此条注意事项而产生的任何后果自负，模块的所有贡献者不负任何责任。

## 功能特性

- 🔄 **智能同步**: 优化的同步服务，支持增量同步和中断恢复
- 📊 **完整数据管理**: 存储视频、UP主、统计数据、收藏关系等完整信息
- 🖼️ **封面管理**: 自动下载并本地化管理视频封面图片
- 🗑️ **删除检测**: 自动检测已失效视频并记录删除日志
- 🎬 **官方影视识别**: 自动识别和分类B站官方影视作品
- 🌐 **现代化Web界面**: 基于FastAPI + Jinja2的响应式Web管理界面
- 🔍 **高级搜索**: 支持视频搜索、状态过滤、分页查询
- 📈 **详细统计**: 收藏夹、视频、官方影视作品的多维度统计分析
- 🛠️ **完整CLI工具**: 基于Click + Rich的美观命令行管理工具
- 📝 **错误追踪**: 详细的错误栈信息记录和调试支持
- 🔧 **数据库优化**: SQLite WAL模式、连接池、自动迁移等性能优化

## 项目结构

```
bilibili-my-favorite/
├── src/                                    # 源代码目录
│   ├── cli.py                              # 命令行工具入口
│   └── bilibili_my_favorite/               # 主要源代码包
│       ├── __init__.py                     # 包初始化文件
│       ├── app.py                          # FastAPI应用主文件
│       ├── core/                           # 核心配置层
│       │   ├── __init__.py
│       │   └── config.py                   # 配置管理和环境变量
│       ├── models/                         # 数据模型层
│       │   ├── __init__.py
│       │   ├── database.py                 # 数据库模型和表结构定义
│       │   └── database_migration.py       # 数据库迁移脚本
│       ├── dao/                            # 数据访问层 (DAO)
│       │   ├── __init__.py
│       │   ├── base.py                     # 基础DAO类和数据库连接管理
│       │   ├── collection_dao.py           # 收藏夹数据访问操作
│       │   └── video_dao.py                # 视频数据访问操作
│       ├── services/                       # 业务逻辑层
│       │   ├── __init__.py
│       │   ├── bilibili_service.py         # B站API服务封装
│       │   ├── optimized_sync_service.py   # 优化的同步服务
│       │   └── sync_context.py             # 同步上下文和状态管理
│       ├── api/                            # API路由层
│       │   ├── __init__.py
│       │   ├── models.py                   # API数据模型和响应格式
│       │   ├── collections.py              # 收藏夹API路由
│       │   └── videos.py                   # 视频API路由
│       └── utils/                          # 工具层
│           ├── __init__.py
│           ├── logger.py                   # 日志配置和工具
│           └── downloader.py               # 文件下载工具
├── data/                                   # 同步数据临时存储
├── covers/                                 # 视频封面图片存储
├── logs/                                   # 应用日志文件
├── .env                                    # 环境变量配置
├── .gitignore                              # Git忽略文件配置
├── .python-version                         # Python版本指定
├── bilibili_favorites.db                   # SQLite主数据库
├── bilibili_favorites.db-wal               # SQLite WAL日志文件
├── bilibili_favorites.db-shm               # SQLite共享内存文件
├── pyproject.toml                          # 项目配置和依赖管理
├── uv.lock                                 # 依赖锁定文件
├── README.md                               # 项目说明文档
├── LICENSE                                 # 开源许可证
└── web_server.py                           # 独立Web服务器启动脚本
```

## 安装和配置

### 1. 环境要求

- Python 3.12+
- uv (推荐) 或 pip

### 2. 克隆项目

```bash
git clone <repository-url>
cd bilibili-my-favorite
```

### 3. 安装依赖

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

### 4. 配置环境变量

创建 `.env` 文件并配置B站API凭据：

```env
# B站API凭据 (必需)
USER_DEDE_USER_ID=your_user_id
USER_SESSDATA=your_sessdata
USER_BILI_JCT=your_bili_jct
USER_BUVID3=your_buvid3
USER_AC_TIME_VALUE=your_ac_time_value

# Web服务器配置 (可选)
WEB_HOST=127.0.0.1
WEB_PORT=8000
DEBUG=false

# 下载配置 (可选)
DOWNLOAD_TIMEOUT=10
MAX_PAGES_PER_COLLECTION=50
REQUEST_DELAY=0.5

# 日志配置 (可选)
LOG_LEVEL=INFO
```

### 5. 获取B站凭据

1. 登录B站网页版
2. 打开浏览器开发者工具 (F12)
3. 在Network标签页中找到任意请求
4. 在请求头中找到Cookie字段，提取以下值：
   - `DedeUserID` → `USER_DEDE_USER_ID`
   - `SESSDATA` → `USER_SESSDATA`
   - `bili_jct` → `USER_BILI_JCT`
   - `buvid3` → `USER_BUVID3`
   - `ac_time_value` → `USER_AC_TIME_VALUE`

## 使用方法

### 命令行工具

```bash
# 初始化数据库
python src/cli.py init-db

# 同步所有收藏夹
python src/cli.py sync

# 同步指定收藏夹
python src/cli.py sync -c 收藏夹ID

# 列出所有收藏夹
python src/cli.py list-collections

# 列出收藏夹中的视频
python src/cli.py list-videos 收藏夹ID

# 列出官方影视作品
python src/cli.py list-official

# 列出最近被删除的视频
python src/cli.py list-deleted

# 显示统计信息（包含官方影视作品统计）
python src/cli.py stats

# 启动Web服务器
python src/cli.py serve

# 清理中断的同步任务
python src/cli.py clean

# 查看帮助
python src/cli.py --help
```

### Web界面

启动Web服务器后，访问 `http://localhost:8000` 使用Web界面：

- **首页**: 查看所有收藏夹概览
- **收藏夹详情**: 查看收藏夹中的视频列表，支持搜索和过滤
- **同步管理**: 执行同步操作，查看同步进度和结果
- **统计信息**: 查看详细的数据统计和分析
- **官方影视**: 专门的官方影视作品管理页面

### 独立Web服务器

```bash
# 使用独立Web服务器脚本
python web_server.py

# 或直接使用uvicorn
uvicorn src.bilibili_my_favorite.app:app --host 0.0.0.0 --port 8000
```

### API接口

系统提供完整的REST API，访问 `http://localhost:8000/docs` 查看交互式API文档。

#### 主要端点

**收藏夹相关**：
- `GET /api/collections/` - 获取收藏夹列表
- `GET /api/collections/{id}` - 获取收藏夹详情
- `GET /api/collections/{id}/stats` - 获取收藏夹统计信息
- `POST /api/collections/sync` - 同步收藏夹
- `POST /api/collections/{id}/sync` - 同步指定收藏夹
- `DELETE /api/collections/{id}` - 删除收藏夹

**视频相关**：
- `GET /api/videos/collections/{id}` - 获取收藏夹视频列表
- `GET /api/videos/{id}` - 获取视频详情
- `GET /api/videos/bvid/{bvid}` - 根据BVID获取视频
- `GET /api/videos/official` - 获取官方影视作品列表
- `GET /api/videos/deleted` - 获取已删除视频列表
- `GET /api/videos/stats` - 获取视频统计信息

## 数据库结构

系统使用SQLite数据库，采用WAL模式优化性能，包含以下主要表：

### 核心表结构

- **users**: 用户信息 (id, mid, name, face_url, jump_link, created_at, updated_at)
- **collections**: 收藏夹信息 (id, bilibili_fid, title, user_mid, description, cover_url, media_count, last_synced, created_at, updated_at)
- **uploaders**: UP主信息 (id, mid, name, face_url, jump_link, created_at, updated_at)
- **videos**: 视频详细信息 (包含官方影视作品标识、删除状态等)
- **collection_videos**: 收藏关系表 (多对多关系)
- **video_stats**: 视频统计信息 (播放量、点赞数等)
- **deletion_logs**: 删除记录日志 (追踪被删除的视频)

### 重要字段说明

- **videos.ogv_info**: 官方影视作品信息 (JSON格式)
- **videos.season_info**: 番剧/电视剧季度信息 (JSON格式)
- **videos.is_deleted**: 全局删除状态标识
- **videos.deleted_at**: 删除时间戳

## 核心功能详解

### 智能同步服务

- **增量同步**: 只同步变更的数据，提高效率
- **中断恢复**: 支持同步任务的中断和恢复
- **错误处理**: 完整的错误栈追踪和日志记录
- **删除检测**: 自动检测并记录被删除的视频
- **状态管理**: 详细的同步状态和进度追踪

### 官方影视作品管理

- **自动识别**: 通过ogv_info字段自动识别官方影视作品
- **分类管理**: 区分电影、电视剧、纪录片等类型
- **专门统计**: 独立的官方影视作品统计分析
- **专用接口**: 专门的API接口和CLI命令

### 数据库优化

- **WAL模式**: 启用Write-Ahead Logging提高并发性能
- **连接管理**: 单例模式的数据库连接管理
- **自动迁移**: 应用启动时自动检查并执行数据库迁移
- **性能调优**: 优化缓存大小、同步模式等参数

## 开发指南

### 项目架构

项目采用现代化的分层架构设计：

1. **核心配置层** (`core/`): 统一管理应用配置、环境变量和全局设置
2. **API路由层** (`api/`): 处理HTTP请求响应、数据验证和路由分发
3. **业务逻辑层** (`services/`): 核心业务逻辑、同步服务、事务处理和状态管理
4. **数据访问层** (`dao/`): 数据库操作抽象、SQL查询和连接管理
5. **数据模型层** (`models/`): 数据结构定义、数据库初始化和迁移脚本
6. **工具层** (`utils/`): 通用功能模块，如日志记录、文件下载等
7. **CLI层** (`cli.py`): 命令行接口，提供完整的管理工具集

### 添加新功能

1. 在相应的层级添加代码
2. 更新API路由和数据模型
3. 添加相应的测试
4. 更新文档和配置

### 代码规范

- **语言**: 所有注释、文档字符串、日志信息使用中文
- **编码规范**: 遵循PEP 8，使用类型提示
- **错误处理**: 使用结构化异常处理，记录完整错误栈
- **异步编程**: 所有数据库操作和HTTP请求使用异步方法
- **日志规范**: 使用统一的日志工具，包含详细的调试信息

### 扩展开发

#### 添加新API端点
1. 在 `src/bilibili_my_favorite/api/` 下创建或修改路由文件
2. 在 `src/bilibili_my_favorite/api/models.py` 中定义数据模型
3. 在 `src/bilibili_my_favorite/app.py` 中注册路由

#### 添加新服务
1. 在 `src/bilibili_my_favorite/services/` 下创建服务类
2. 实现业务逻辑方法
3. 在相应的API路由中调用

#### 数据库迁移
1. 修改 `src/bilibili_my_favorite/models/database.py` 中的表结构
2. 在 `src/bilibili_my_favorite/models/database_migration.py` 中实现迁移脚本
3. 测试迁移过程和数据完整性

## 性能优化

### 数据库优化
- SQLite WAL模式启用
- 连接池和长连接管理
- 内存映射和缓存优化
- 批量操作和事务管理

### 同步优化
- 增量同步策略
- 并发控制和限流
- 错误重试机制
- 中断恢复支持

### Web性能
- 异步请求处理
- 分页查询支持
- 静态资源优化
- 缓存策略

## 常见问题

### Q: 同步失败怎么办？
A: 
1. 检查B站凭据是否正确和有效
2. 确保网络连接正常
3. 查看 `logs/` 目录中的日志文件获取详细错误信息
4. 使用 `python src/cli.py clean` 清理中断的同步任务

### Q: 如何备份数据？
A: 
1. 复制整个 `bilibili_favorites.db*` 数据库文件（包括WAL和SHM文件）
2. 备份 `covers/` 目录中的封面图片
3. 备份 `.env` 配置文件

### Q: 可以同时运行多个实例吗？
A: 不建议，因为会共享同一个数据库文件，可能导致数据冲突。如需多实例，请使用不同的数据库文件。

### Q: 如何定期自动同步？
A: 可以使用系统的定时任务：
- Linux/macOS: 使用 cron 定时执行 `python src/cli.py sync`
- Windows: 使用任务计划程序定时执行同步命令

### Q: 官方影视作品如何识别？
A: 系统通过视频的 `ogv_info` 字段自动识别官方影视作品，包括电影、电视剧、纪录片等。

### Q: 删除的视频如何查看？
A: 使用 `python src/cli.py list-deleted` 命令或访问Web界面的删除记录页面。

## 技术栈

### 核心框架
- **Web框架**: FastAPI 0.110.0+
- **数据库**: SQLite + aiosqlite 0.20.0+
- **模板引擎**: Jinja2 3.1.4+
- **HTTP客户端**: httpx 0.28.1+
- **B站API**: bilibili-api-python 17.1.4+

### 开发工具
- **依赖管理**: uv
- **CLI框架**: Click 8.1.0+
- **终端美化**: Rich 14.0.0+
- **数据验证**: Pydantic 2.0.0+
- **配置管理**: python-dotenv 1.0.0+
- **HTTP请求**: curl-cffi 0.11.1+

## 许可证

本项目采用 GNU General Public License Version 3 许可证，详见 LICENSE 文件。

## 贡献

欢迎提交Issue和Pull Request来改进项目！请确保：

1. 遵循项目的代码规范
2. 添加适当的测试
3. 更新相关文档
4. 使用中文注释和说明

## 更新日志

### v1.0.0 (当前版本)
- ✨ 完全重构项目架构，采用现代化分层设计
- 🚀 新增优化的同步服务，支持增量同步和中断恢复
- 🎬 新增官方影视作品识别和管理功能
- 📝 新增详细的错误栈追踪和调试支持
- 🗑️ 新增删除视频的详细记录和追踪
- 🔧 优化数据库性能，启用WAL模式和连接管理
- 🌐 改进Web界面，提供更好的用户体验
- 🛠️ 完善CLI工具，使用Rich美化输出
- 📊 增强统计功能，区分普通视频和官方影视作品
- 🔄 新增自动数据库迁移机制
- 📚 完善项目文档和开发指南

# bilibili 缓存自己的收藏夹

一个用于本地同步和管理B站收藏夹的Web应用系统，支持视频信息同步、封面下载、删除检测等功能。

注意事项：使用此模块时请仅用于学习和测试，禁止用于非法用途及其他恶劣的社区行为如：恶意刷屏、辱骂黄暴、各种形式的滥用等，违规此模块许可证 GNU General Public License Version 3 及此条注意事项而产生的任何后果自负，模块的所有贡献者不负任何责任。


## 功能特性

- 🔄 **自动同步**: 定期同步B站收藏夹数据到本地数据库
- 📊 **数据管理**: 完整的视频信息存储，包括UP主、统计数据等
- 🖼️ **封面下载**: 自动下载并管理视频封面图片
- 🗑️ **删除检测**: 自动检测已失效的视频并标记
- 🌐 **Web界面**: 现代化的Web管理界面
- 🔍 **搜索过滤**: 支持视频搜索和状态过滤
- 📈 **统计分析**: 详细的收藏夹和视频统计信息
- 🛠️ **命令行工具**: 完整的CLI管理工具

## 项目结构

```
bilibili-my-favorite/
├── src/                          # 源代码目录
│   ├── __init__.py
│   ├── config.py                 # 配置管理
│   ├── app.py                    # FastAPI应用主文件
│   ├── cli.py                    # 命令行工具
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   └── database.py           # 数据库模型和操作
│   ├── dao/                      # 数据访问层
│   │   ├── __init__.py
│   │   ├── base.py               # 基础DAO类
│   │   ├── collection_dao.py     # 收藏夹数据访问
│   │   └── video_dao.py          # 视频数据访问
│   ├── services/                 # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── bilibili_service.py   # B站API服务
│   │   └── sync_service.py       # 同步服务
│   ├── api/                      # API路由层
│   │   ├── __init__.py
│   │   ├── models.py             # API数据模型
│   │   ├── collections.py        # 收藏夹API
│   │   └── videos.py             # 视频API
│   └── utils/                    # 工具类
│       ├── __init__.py
│       ├── logger.py             # 日志工具
│       └── downloader.py         # 下载工具
├── templates/                    # HTML模板
├── covers/                       # 封面图片存储
├── logs/                         # 日志文件
├── .env                          # 环境变量配置
├── pyproject.toml               # 项目配置
└── README.md                    # 项目说明
```

## 安装和配置

### 1. 克隆项目

```bash
git clone <repository-url>
cd bilibili-my-favorite
```

### 2. 安装依赖

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

### 3. 配置环境变量

创建 `.env` 文件并配置B站API凭据：

```env
# B站API凭据 (必需)
USER_DEDE_USER_ID=your_user_id
USER_SESSDATA=your_sessdata
USER_BILI_JCT=your_bili_jct
USER_BUVID3=your_buvid3
USER_AC_TIME_VALUE=your_ac_time_value

# Web服务器配置 (可选)
WEB_HOST=127.0.0.1
WEB_PORT=8000
DEBUG=false

# 下载配置 (可选)
DOWNLOAD_TIMEOUT=10
MAX_PAGES_PER_COLLECTION=50
REQUEST_DELAY=0.5

# 日志配置 (可选)
LOG_LEVEL=INFO
```

### 4. 获取B站凭据

1. 登录B站网页版
2. 打开浏览器开发者工具 (F12)
3. 在Network标签页中找到任意请求
4. 在请求头中找到Cookie字段，提取以下值：
   - `DedeUserID` → `USER_DEDE_USER_ID`
   - `SESSDATA` → `USER_SESSDATA`
   - `bili_jct` → `USER_BILI_JCT`
   - `buvid3` → `USER_BUVID3`
   - `ac_time_value` → `USER_AC_TIME_VALUE`

## 使用方法

### 命令行工具

```bash
# 初始化数据库
bilibili-favorites init-db

# 同步所有收藏夹
bilibili-favorites sync

# 同步指定收藏夹
bilibili-favorites sync -c 收藏夹ID

# 列出所有收藏夹
bilibili-favorites list-collections

# 列出收藏夹中的视频
bilibili-favorites list-videos 收藏夹ID

# 显示统计信息
bilibili-favorites stats

# 启动Web服务器
bilibili-favorites serve

# 查看帮助
bilibili-favorites --help
```

### Web界面

启动Web服务器后，访问 `http://localhost:8000` 使用Web界面：

- **首页**: 查看所有收藏夹
- **收藏夹详情**: 查看收藏夹中的视频列表
- **同步管理**: 执行同步操作
- **统计信息**: 查看详细统计数据

### API接口

系统提供完整的REST API，访问 `http://localhost:8000/docs` 查看API文档。

主要端点：
- `GET /api/collections/` - 获取收藏夹列表
- `GET /api/collections/{id}` - 获取收藏夹详情
- `POST /api/collections/sync` - 同步收藏夹
- `GET /api/videos/collections/{id}` - 获取收藏夹视频
- `GET /api/videos/{id}` - 获取视频详情

## 数据库结构

系统使用SQLite数据库，包含以下主要表：

- **users**: 用户信息
- **collections**: 收藏夹信息
- **uploaders**: UP主信息
- **videos**: 视频详细信息
- **collection_videos**: 收藏关系 (多对多)
- **video_stats**: 视频统计信息
- **deletion_logs**: 删除记录日志

## 开发指南

### 项目架构

项目采用分层架构设计：

1. **API层** (`src/api/`): 处理HTTP请求和响应
2. **服务层** (`src/services/`): 业务逻辑处理
3. **数据访问层** (`src/dao/`): 数据库操作抽象
4. **数据模型层** (`src/models/`): 数据库模型定义
5. **工具层** (`src/utils/`): 通用工具函数

### 添加新功能

1. 在相应的层级添加代码
2. 更新API路由和数据模型
3. 添加相应的测试
4. 更新文档

### 代码规范

- 使用中文注释和文档字符串
- 遵循PEP 8代码风格
- 使用类型提示
- 编写单元测试

## 常见问题

### Q: 同步失败怎么办？
A: 检查B站凭据是否正确，确保网络连接正常，查看日志文件获取详细错误信息。

### Q: 如何备份数据？
A: 直接复制 `bilibili_favorites.db` 数据库文件和 `covers/` 目录即可。

### Q: 可以同时运行多个实例吗？
A: 不建议，因为会共享同一个数据库文件，可能导致数据冲突。

### Q: 如何定期自动同步？
A: 可以使用系统的定时任务 (cron/Task Scheduler) 定期执行 `bilibili-favorites sync` 命令。

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 贡献

欢迎提交Issue和Pull Request来改进项目！ 