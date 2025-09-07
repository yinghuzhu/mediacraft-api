#!/bin/bash
# MediaCraft 生产环境部署脚本 v2.7.0
# 支持 API 路由修复和视频合并任务处理改进

set -e

VERSION="2.7.0"
PROJECT_NAME="mediacraft-api"
DEPLOY_USER="yhzhu"
DEPLOY_PATH="/home/${DEPLOY_USER}/${PROJECT_NAME}"
# BACKUP_DIR="/tmp/${PROJECT_NAME}_backup_$(date +%Y%m%d_%H%M%S)"
DATA_DIR=/data/mediacraft

echo "🚀 MediaCraft v${VERSION} 生产环境部署"
echo "========================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查是否以正确用户运行
if [ "$USER" != "$DEPLOY_USER" ]; then
    print_error "请以 $DEPLOY_USER 用户运行此脚本"
    exit 1
fi

# 检查依赖
echo "🔍 检查系统依赖..."
command -v python3 >/dev/null 2>&1 || { print_error "需要安装 Python 3"; exit 1; }
command -v git >/dev/null 2>&1 || { print_error "需要安装 Git"; exit 1; }

# 详细检查FFmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    print_success "FFmpeg 已安装"
else
    print_error "FFmpeg 未安装！视频合并功能将无法使用"
    echo ""
    echo "安装FFmpeg:"
    echo "Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg"
    echo "CentOS/RHEL 7: sudo yum install epel-release && sudo yum install ffmpeg"
    echo "RHEL 8+/Rocky Linux/AlmaLinux:"
    echo "  sudo dnf install epel-release -y"
    echo "  sudo dnf config-manager --set-enabled crb"
    echo "  sudo dnf install https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-9.noarch.rpm -y"
    echo "  sudo dnf install ladspa ffmpeg ffmpeg-devel -y"
    echo "macOS:         brew install ffmpeg"
    echo ""
    echo "🔍 For Rocky Linux 9 specific issues, see: issues/ROCKY_LINUX_FFMPEG_INSTALLATION.md"
    echo ""
    read -p "是否继续部署？(y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_success "系统依赖检查完成"

# 检查当前运行状态
if pgrep -f "python.*app.py" > /dev/null; then
    print_warning "检测到正在运行的 MediaCraft 服务"
    
    # 创建备份
    # echo "📦 创建数据备份..."
    # mkdir -p "$BACKUP_DIR"
    # if [ -d "$DEPLOY_PATH" ]; then
    #     # 只备份重要数据
    #     cp -r "$DEPLOY_PATH/data" "$BACKUP_DIR/" 2>/dev/null || true
    #     cp "$DEPLOY_PATH/.env.production" "$BACKUP_DIR/" 2>/dev/null || true
    #     print_success "数据备份已创建: $BACKUP_DIR"
    # fi
    
    # 优雅停止服务
    echo "🛑 停止现有服务..."
    pkill -TERM -f "python.*app.py" || true
    sleep 5
    pkill -KILL -f "python.*app.py" 2>/dev/null || true
    sleep 2
fi

# 部署代码
echo "📦 部署应用代码..."

# 确保部署目录存在
mkdir -p "$(dirname $DEPLOY_PATH)"

if [ -d "$DEPLOY_PATH" ]; then
    cd "$DEPLOY_PATH"
    
    # 更新代码
    echo "📥 拉取最新代码..."
    git fetch origin
    git reset --hard origin/master
else
    # 首次克隆
    echo "📥 克隆代码仓库..."
    git clone https://github.com/yinghuzhu/mediacraft-api.git "$DEPLOY_PATH"
    cd "$DEPLOY_PATH"
fi

print_success "代码部署完成"

# 设置虚拟环境
echo "🔧 配置 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "虚拟环境已创建"
fi

source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install -r requirements.txt

print_success "依赖安装完成"

# 恢复数据和配置
# if [ -d "$BACKUP_DIR" ]; then
#     echo "🔄 恢复数据和配置..."
#     cp -r "$BACKUP_DIR/data" . 2>/dev/null || true
#     cp "$BACKUP_DIR/.env.production" . 2>/dev/null || true
#     print_success "数据恢复完成"
# fi

# 检查生产环境配置
if [ ! -f ".env.production" ]; then
    print_warning "生产环境配置文件不存在，使用开发配置"
    cp .env.development .env.production
    print_warning "请编辑 .env.production 文件设置生产环境参数"
fi

# 设置权限
# echo "🔐 设置文件权限..."
# chmod +x *.sh
# chmod 600 .env.*
# mkdir -p data/{uploads,results,temp,logs}
# chmod 755 data/
# chmod 777 data/{uploads,results,temp,logs}

# print_success "权限设置完成"

# # 运行数据库迁移/初始化（如果需要）
# echo "🗄️  初始化数据存储..."
# mkdir -p data/{uploads,results,temp,logs}
# touch data/tasks.json 2>/dev/null || true
# touch data/users.json 2>/dev/null || true
# touch data/sessions.json 2>/dev/null || true

# 启动服务
echo "🚀 启动 MediaCraft 服务..."
export FLASK_ENV=production
nohup python3 app.py > ${DATA_DIR}/logs/app.log 2>&1 &

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 健康检查
echo "🔍 运行健康检查..."
for i in {1..12}; do
    if curl -f -s http://127.0.0.1:50001/api/system/status > /dev/null; then
        print_success "服务健康检查通过"
        break
    fi
    
    if [ $i -eq 12 ]; then
        print_error "服务启动失败！"
        echo "📋 检查日志: tail -f $DEPLOY_PATH/data/logs/app.log"
        exit 1
    fi
    
    echo "等待服务启动... ($i/12)"
    sleep 5
done

# 运行自定义健康检查
if [ -f "health_check.py" ]; then
    echo "🏥 运行系统清理..."
    python3 health_check.py
fi

# 运行FFmpeg检查
if [ -f "check_ffmpeg.py" ]; then
    echo "🎥 检查FFmpeg状态..."
    python3 check_ffmpeg.py
fi

# 部署完成
echo ""
echo "🎉 部署完成！"
echo "================================"
echo "📊 版本: v${VERSION}"
echo "📁 部署路径: $DEPLOY_PATH"
echo "🌐 API地址: http://127.0.0.1:50001"
echo "📋 备份位置: $BACKUP_DIR"
echo "📝 应用日志: $DEPLOY_PATH/data/logs/app.log"
echo "📝 错误日志: $DEPLOY_PATH/data/logs/error.log"
echo ""
echo "🔧 后续操作:"
echo "1. 检查 Nginx 配置是否正确"
echo "2. 确保 SSL 证书有效"
echo "3. 监控应用日志"
echo "4. 测试前端功能"
echo ""
echo "📋 常用命令:"
echo "查看日志: tail -f $DEPLOY_PATH/data/logs/app.log"
echo "重启服务: cd $DEPLOY_PATH && ./deploy_to_production_v2.sh"
echo "检查状态: curl http://127.0.0.1:50001/api/system/status"