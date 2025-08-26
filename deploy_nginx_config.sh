#!/bin/bash

# MediaCraft Nginx 配置部署脚本
# 使用方法: sudo bash deploy_nginx_config.sh

set -e

CONFIG_FILE="/usr/local/nginx/conf/vhost/mediacraft.yzhu.name.conf"
BACKUP_FILE="/usr/local/nginx/conf/vhost/mediacraft.yzhu.name.conf.backup.$(date +%Y%m%d_%H%M%S)"
NEW_CONFIG="updated_mediacraft_nginx.conf"

echo "🚀 开始部署 MediaCraft Nginx 配置..."

# 检查是否以 root 权限运行
if [[ $EUID -ne 0 ]]; then
   echo "❌ 错误: 请使用 sudo 运行此脚本"
   exit 1
fi

# 检查新配置文件是否存在
if [[ ! -f "$NEW_CONFIG" ]]; then
    echo "❌ 错误: 找不到新配置文件 $NEW_CONFIG"
    exit 1
fi

# 检查 MediaCraft 服务状态
echo "🔍 检查 MediaCraft 服务状态..."
if ! systemctl is-active --quiet mediacraft-backend 2>/dev/null; then
    echo "⚠️  警告: mediacraft-backend 服务未运行"
    echo "   请确保后端服务在端口 50001 上运行"
fi

if ! systemctl is-active --quiet mediacraft-frontend 2>/dev/null; then
    echo "⚠️  警告: mediacraft-frontend 服务未运行"
    echo "   请确保前端服务在端口 3000 上运行"
fi

# 检查端口是否被监听
echo "🔍 检查端口状态..."
if ! netstat -tlnp | grep -q ":3000 "; then
    echo "⚠️  警告: 端口 3000 未被监听"
fi

if ! netstat -tlnp | grep -q ":50001 "; then
    echo "⚠️  警告: 端口 50001 未被监听"
fi

# 备份现有配置
echo "💾 备份现有配置..."
if [[ -f "$CONFIG_FILE" ]]; then
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo "✅ 配置已备份到: $BACKUP_FILE"
else
    echo "⚠️  警告: 原配置文件不存在，将创建新文件"
fi

# 复制新配置
echo "📝 应用新配置..."
cp "$NEW_CONFIG" "$CONFIG_FILE"

# 测试 Nginx 配置
echo "🧪 测试 Nginx 配置..."
if nginx -t; then
    echo "✅ Nginx 配置测试通过"
    
    # 重新加载 Nginx
    echo "🔄 重新加载 Nginx..."
    if nginx -s reload; then
        echo "✅ Nginx 配置已成功应用"
        
        # 验证配置
        echo "🔍 验证配置..."
        sleep 2
        
        # 测试 HTTPS 访问
        if curl -k -s -o /dev/null -w "%{http_code}" https://mediacraft.yzhu.name | grep -q "200\|301\|302"; then
            echo "✅ HTTPS 访问正常"
        else
            echo "⚠️  警告: HTTPS 访问可能有问题"
        fi
        
        echo ""
        echo "🎉 部署完成！"
        echo ""
        echo "📋 验证清单:"
        echo "  1. 访问 https://mediacraft.yzhu.name"
        echo "  2. 测试 API: https://mediacraft.yzhu.name/api/health"
        echo "  3. 检查文件上传功能"
        echo ""
        echo "📊 监控命令:"
        echo "  - 查看访问日志: tail -f /home/wwwlogs/mediacraft.yzhu.name.log"
        echo "  - 查看错误日志: tail -f /home/wwwlogs/mediacraft.yzhu.name.error.log"
        echo ""
        echo "🔄 如需回滚:"
        echo "  sudo cp $BACKUP_FILE $CONFIG_FILE && sudo nginx -s reload"
        
    else
        echo "❌ 错误: Nginx 重新加载失败"
        echo "🔄 正在回滚配置..."
        cp "$BACKUP_FILE" "$CONFIG_FILE"
        nginx -s reload
        exit 1
    fi
else
    echo "❌ 错误: Nginx 配置测试失败"
    echo "🔄 正在回滚配置..."
    if [[ -f "$BACKUP_FILE" ]]; then
        cp "$BACKUP_FILE" "$CONFIG_FILE"
    fi
    exit 1
fi