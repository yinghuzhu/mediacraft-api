# MediaCraft Backend

MediaCraft 视频处理平台的后端服务，提供视频合并和水印去除功能。

## 功能特性

- 🎬 视频合并处理
- 🖼️ 智能水印去除
- 📊 任务队列管理
- 👥 用户会话管理
- 🔄 实时处理状态

## 技术栈

- **框架**: Flask
- **视频处理**: FFmpeg, OpenCV
- **任务队列**: 内置任务管理系统
- **存储**: 本地文件系统
- **部署**: Nginx + Gunicorn

## 快速开始

### 环境要求

- Python 3.8+
- FFmpeg
- OpenCV

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

复制并编辑环境配置文件：

```bash
cp .env.development .env
```

### 启动服务

```bash
# 开发环境
python app.py

# 生产环境
./start_backend.sh
```

## API 文档

### 核心端点

- `POST /api/video/merge` - 视频合并
- `POST /api/video/watermark/remove` - 水印去除
- `GET /api/tasks/{task_id}` - 获取任务状态
- `GET /api/tasks/{task_id}/download` - 下载处理结果

### 用户管理

- `POST /api/user/register` - 用户注册
- `POST /api/user/login` - 用户登录
- `GET /api/user/profile` - 获取用户信息

## 部署

### 生产环境部署

1. 配置环境变量
2. 安装依赖
3. 配置Nginx
4. 启动服务

```bash
./deploy_to_production.sh
```

## 项目结构

```
├── api/                 # API路由
├── core/               # 核心功能模块
├── processors/         # 视频处理器
├── models/            # 数据模型
├── data/              # 数据存储
├── tests/             # 测试文件
├── app.py             # 主应用入口
├── config.py          # 配置文件
└── requirements.txt   # 依赖列表
```

## 环境变量

```bash
# 服务配置
FLASK_ENV=production
HOST=0.0.0.0
PORT=5000

# 文件存储
UPLOAD_FOLDER=data/uploads
RESULT_FOLDER=data/results
MAX_CONTENT_LENGTH=500MB

# 任务配置
MAX_CONCURRENT_TASKS=3
TASK_TIMEOUT=3600
```

## 许可证

MIT License