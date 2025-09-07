# 生产环境视频合并FFmpeg问题解决方案

## 🚨 问题描述
生产环境视频合并任务失败，错误信息：`[Errno 2] No such file or directory: 'ffmpeg'`

## 🔍 问题原因
生产服务器上未安装FFmpeg，而视频合并功能需要FFmpeg来执行视频切割和合并操作。

## ✅ 解决方案

### 方案一：安装FFmpeg（推荐）

#### Ubuntu/Debian系统：
```bash
sudo apt update
sudo apt install ffmpeg
```

#### CentOS/RHEL系统：
```bash
# CentOS 7
sudo yum install epel-release
sudo yum install ffmpeg

# CentOS 8+/RHEL 8+
sudo dnf install ffmpeg
```

#### 验证安装：
```bash
ffmpeg -version
which ffmpeg
```

### 方案二：使用检查脚本

运行FFmpeg检查脚本确认安装状态：
```bash
cd /home/yhzhu/mediacraft-api
python3 check_ffmpeg.py
```

### 方案三：重新部署（包含FFmpeg检查）

使用更新后的部署脚本，它会检查FFmpeg并提供安装指导：
```bash
cd /home/yhzhu/mediacraft-api
./deploy_to_production_v2.sh
```

## 🔧 已实现的改进

1. **FFmpeg可用性检查**：添加了FFmpeg安装检查函数
2. **优雅降级**：如果FFmpeg不可用，提供清晰的错误信息
3. **部署脚本改进**：部署时强制检查FFmpeg安装状态
4. **健康检查脚本**：创建专门的FFmpeg检查工具

## 📋 验证步骤

1. 安装FFmpeg后验证：
```bash
ffmpeg -version
python3 check_ffmpeg.py
```

2. 测试视频合并功能：
```bash
curl -X POST http://127.0.0.1:50001/api/tasks/submit \
  -F "task_type=video_merge" \
  -F "file=@test1.mp4" \
  -F "file=@test2.mp4"
```

3. 检查服务日志：
```bash
tail -f /data/mediacraft/logs/app.log
```

## 🚀 后续维护

- 在服务器环境文档中记录FFmpeg依赖
- 定期运行`check_ffmpeg.py`验证FFmpeg状态
- 监控视频处理任务的成功率

## 🆘 紧急处理

如果暂时无法安装FFmpeg，系统会：
1. 记录清晰的错误信息
2. 避免系统崩溃
3. 提供用户友好的错误提示

但视频合并功能将完全不可用，直到FFmpeg安装完成。