#!/bin/bash
# MediaCraft 后端启动脚本

echo "启动 MediaCraft 后端服务..."
echo "================================"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "错误: 虚拟环境不存在，请先创建虚拟环境"
    echo "运行: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖
echo "检查依赖..."
python -c "import flask, cv2, numpy; print('✓ 所有依赖已安装')" || {
    echo "安装依赖..."
    pip install -r requirements.txt
}

# 检查配置文件
if [ ! -f ".env.development" ]; then
    echo "警告: .env.development 文件不存在，将使用默认配置"
fi

# 验证配置
echo "验证配置..."
python scripts/validate_config.py || {
    echo "配置验证失败，请检查配置文件"
    exit 1
}

echo ""
echo "启动后端服务..."
echo "配置文件: .env.development"
echo "服务地址: http://127.0.0.1:50001"
echo "健康检查: http://127.0.0.1:50001/api/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 设置环境变量
export FLASK_ENV=development

# 启动应用
python app.py