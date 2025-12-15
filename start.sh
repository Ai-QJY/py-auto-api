#!/bin/bash

# py-auto-api 启动脚本

set -e

echo "🚀 启动 py-auto-api 服务..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查是否在虚拟环境中
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "📦 建议在虚拟环境中运行"
fi

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt

# 创建必要的目录
echo "📁 创建目录..."
mkdir -p logs uploads

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 启动服务
echo "🌟 启动FastAPI服务..."
echo "📱 前端地址: http://localhost:8000"
echo "📖 API文档: http://localhost:8000/docs"
echo "🔧 可视化编辑器: http://localhost:8000/frontend"
echo ""

cd backend
python main.py