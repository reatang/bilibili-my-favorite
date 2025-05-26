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

## 更新日志

### v1.0.0
- 完全重构项目架构
- 新增工程化的代码结构
- 改进数据库设计
- 添加完整的Web API
- 新增命令行工具
- 优化同步性能
- 添加详细的日志和错误处理 