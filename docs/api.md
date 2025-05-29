# API 接口文档

B站收藏夹管理系统提供完整的REST API，支持收藏夹、视频、同步等功能的管理。

## 快速开始

- **交互式文档**: 访问 `http://localhost:8000/docs` 查看Swagger UI
- **API文档**: 访问 `http://localhost:8000/redoc` 查看ReDoc文档
- **健康检查**: `GET /health` 检查服务状态

## API端点

### 收藏夹相关

| 方法 | 端点 | 描述 |
|------|------|------|
| `GET` | `/api/collections/` | 获取收藏夹列表 |
| `GET` | `/api/collections/{id}` | 获取收藏夹详情 |
| `GET` | `/api/collections/{id}/videos` | 获取收藏夹视频列表（支持分页、搜索、状态过滤） |
| `GET` | `/api/collections/{id}/stats` | 获取收藏夹统计信息 |
| `POST` | `/api/collections/sync` | 同步收藏夹（支持全量和单个） |
| `POST` | `/api/collections/{id}/sync` | 同步指定收藏夹 |
| `DELETE` | `/api/collections/{id}` | 删除收藏夹 |

### 视频相关

| 方法 | 端点 | 描述 |
|------|------|------|
| `GET` | `/api/videos/collections/{id}` | 获取收藏夹视频列表（兼容路径） |
| `GET` | `/api/videos/{id}` | 获取视频详情 |
| `GET` | `/api/videos/bvid/{bvid}` | 根据BVID获取视频 |
| `GET` | `/api/videos/{id}/stats` | 获取单个视频统计信息 |
| `POST` | `/api/videos/{id}/restore` | 恢复已删除视频 |
| `DELETE` | `/api/videos/{id}` | 删除视频（标记为已删除） |

### 全局功能

| 方法 | 端点 | 描述 |
|------|------|------|
| `GET` | `/api/sync` | 全局同步端点（兼容） |
| `POST` | `/api/sync` | 执行同步操作 |
| `GET` | `/api/stats` | 获取全局统计信息 |
| `GET` | `/info` | 获取应用信息和配置状态 |

### 前端页面路由

| 方法 | 端点 | 描述 |
|------|------|------|
| `GET` | `/` | 收藏夹列表页面 |
| `GET` | `/collections/{id}` | 收藏夹详情页面 |
| `GET` | `/sync` | 同步管理页面 |
| `GET` | `/stats` | 统计信息页面 |
| `GET` | `/health` | 健康检查端点 |
| `GET` | `/docs` | API交互式文档（Swagger UI） |
| `GET` | `/redoc` | API文档（ReDoc） |

## API参数说明

### 分页参数

- `page`: 页码，从1开始，默认值1
- `page_size`: 每页数量，范围1-100，默认值20

### 视频状态过滤

- `status`: 视频状态过滤
  - `all`: 全部视频（默认）
  - `available`: 可用视频
  - `deleted`: 已删除视频

### 搜索参数

- `search`: 在视频标题和UP主名称中搜索的关键词
  - 最小长度: 1字符
  - 最大长度: 100字符

### 同步请求参数

- `collection_id`: 指定收藏夹ID，为空则同步所有收藏夹
- `force_download_covers`: 是否强制重新下载封面（默认false）

## API响应格式

### 标准响应模型

```json
{
  "id": 1,
  "title": "收藏夹名称",
  "media_count": 100,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 分页响应格式

```json
{
  "items": [...],
  "total": 827,
  "page": 1,
  "page_size": 20,
  "total_pages": 42
}
```

### 同步结果格式

```json
{
  "collections_processed": 1,
  "videos_added": 15,
  "videos_updated": 5,
  "videos_deleted": 2,
  "covers_downloaded": 10,
  "errors": []
}
```

### 错误响应格式

```json
{
  "detail": "错误详细信息",
  "status_code": 404
}
```

## 详细API说明

### 获取收藏夹视频列表

**端点**: `GET /api/collections/{id}/videos`

**参数**:
- `status` (可选): 视频状态过滤 (all/available/deleted)
- `search` (可选): 搜索关键词
- `page` (可选): 页码，默认1
- `page_size` (可选): 每页数量，默认20

**示例**:
```bash
GET /api/collections/123/videos?status=available&search=编程&page=1&page_size=20
```

**响应**:
```json
{
  "items": [
    {
      "id": 1,
      "bvid": "BV1234567890",
      "title": "Python编程教程",
      "uploader_name": "某UP主",
      "fav_time": 1640995200,
      "is_deleted": false
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

### 同步收藏夹

**端点**: `POST /api/collections/sync`

**请求体**:
```json
{
  "collection_id": "123456789",
  "force_download_covers": false
}
```

**响应**:
```json
{
  "collections_processed": 1,
  "videos_added": 15,
  "videos_updated": 5,
  "videos_deleted": 2,
  "covers_downloaded": 10,
  "errors": []
}
```

### 获取全局统计信息

**端点**: `GET /api/stats`

**响应**:
```json
{
  "total_collections": 5,
  "total_videos": 1250,
  "available_videos": 1200,
  "deleted_videos": 50
}
```

## 错误处理

### HTTP状态码

- `200`: 请求成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

### 错误示例

```json
{
  "detail": "收藏夹 123 不存在",
  "status_code": 404
}
```

## 认证

当前版本暂不需要API认证，但建议在生产环境中启用适当的认证机制。

## 速率限制

当前版本暂无速率限制，但建议客户端实现适当的请求间隔以避免对B站API造成压力。

## SDK和工具

### cURL示例

```bash
# 获取收藏夹列表
curl -X GET "http://localhost:8000/api/collections/"

# 搜索视频
curl -X GET "http://localhost:8000/api/collections/123/videos?search=编程&status=available"

# 同步收藏夹
curl -X POST "http://localhost:8000/api/collections/sync" \
  -H "Content-Type: application/json" \
  -d '{"collection_id": "123456789"}'
```

### Python示例

```python
import requests

# 获取收藏夹列表
response = requests.get("http://localhost:8000/api/collections/")
collections = response.json()

# 搜索视频
params = {
    "search": "编程",
    "status": "available",
    "page": 1,
    "page_size": 20
}
response = requests.get(f"http://localhost:8000/api/collections/{collection_id}/videos", params=params)
videos = response.json()

# 同步收藏夹
sync_data = {
    "collection_id": "123456789",
    "force_download_covers": False
}
response = requests.post("http://localhost:8000/api/collections/sync", json=sync_data)
result = response.json()
```

## 更新日志

### v1.0.0
- 初始API版本发布
- 支持收藏夹和视频的基本CRUD操作
- 实现分页、搜索、状态过滤功能
- 支持同步操作和统计信息查询 