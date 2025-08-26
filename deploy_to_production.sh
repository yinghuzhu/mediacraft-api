#!/bin/bash
# MediaCraft v2.6.0 生产环境部署脚本

set -e

VERSION="2.6.2"
RELEASE_FILE="mediacraft-${VERSION}.tar.gz"
BACKUP_DIR="/tmp/mediacraft_backup_$(date +%Y%m%d_%H%M%S)"

echo "🚀 MediaCraft v${VERSION} 生产环境部署"
echo "========================================"

# 检查发布包是否存在
if [ ! -f "releases/${RELEASE_FILE}" ]; then
    echo "❌ 错误: 发布包不存在 releases/${RELEASE_FILE}"
    exit 1
fi

echo "✅ 发现发布包: releases/${RELEASE_FILE}"

# 检查当前是否有运行的服务
if pgrep -f "python3 app.py" > /dev/null; then
    echo "⚠️  检测到正在运行的 MediaCraft 服务"
    echo "📦 创建备份..."
    
    # 创建备份
    mkdir -p "$BACKUP_DIR"
    if [ -d "/home/yhzhu/mediacraft" ]; then
        cp -r /home/yhzhu/mediacraft "$BACKUP_DIR/"
        echo "✅ 备份已创建: $BACKUP_DIR"
    fi
    
    # 停止服务
    echo "🛑 停止现有服务..."
    pkill -f "python3 app.py" || true
    sleep 2
fi

# 部署新版本
echo "📦 部署新版本..."
cd /home/yhzhu

# 解压新版本
tar -xzf "$(pwd)/mediacraft/releases/${RELEASE_FILE}"

# 备份数据目录
if [ -d "mediacraft/data" ]; then
    echo "💾 保留数据目录..."
    cp -r mediacraft/data "mediacraft-${VERSION}/"
fi

# 替换旧版本
if [ -d "mediacraft_old" ]; then
    rm -rf mediacraft_old
fi

if [ -d "mediacraft" ]; then
    mv mediacraft mediacraft_old
fi

mv "mediacraft-${VERSION}" mediacraft

echo "🔧 配置环境..."
cd mediacraft

# 激活虚拟环境
if [ -d "../mediacraft_old/venv" ]; then
    echo "📋 复制虚拟环境..."
    cp -r ../mediacraft_old/venv ./
fi

# 安装依赖
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "⚠️  虚拟环境不存在，请手动创建"
fi

# 启动服务
echo "🚀 启动服务..."
source venv/bin/activate
nohup python3 app.py > app.log 2>&1 &

# 等待服务启动
sleep 5

# 验证服务
echo "🔍 验证服务状态..."
if curl -f -s http://localhost:50001/health > /dev/null; then
    echo "✅ 服务启动成功!"
    echo "🌐 MediaCraft 现在运行在: http://localhost:50001"
    
    # 运行健康检查
    if [ -f "health_check.py" ]; then
        echo "🏥 运行健康检查..."
        python3 health_check.py
    fi
    
    echo ""
    echo "🎉 部署完成!"
    echo "📊 版本: v${VERSION}"
    echo "📁 安装目录: $(pwd)"
    echo "📋 备份目录: $BACKUP_DIR"
    echo "📝 日志文件: $(pwd)/app.log"
    
else
    echo "❌ 服务启动失败!"
    echo "📋 检查日志: tail -f $(pwd)/app.log"
    echo "🔄 如需回滚: mv mediacraft_old mediacraft"
    exit 1
fi