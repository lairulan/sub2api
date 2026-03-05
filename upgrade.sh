#!/bin/bash

echo "=== Sub2API 一键升级脚本 ==="
echo ""

# 切换到目录
cd /opt/sub2api || cd ~

# 如果目录不存在或不是git仓库，则重新克隆
if [ ! -d ".git" ]; then
    echo "正在初始化 Git 仓库..."
    rm -rf sub2api
    git clone https://github.com/lairulan/sub2api.git /opt/sub2api
    cd /opt/sub2api
fi

echo "正在拉取最新代码..."
git fetch origin
git checkout -f main
git pull origin main

echo "正在拉取 Docker 镜像..."
docker-compose -f docker-compose.local.yml pull

echo "正在重启服务..."
docker-compose -f docker-compose.local.yml up -d

echo ""
echo "=== 升级完成 ==="
echo "请访问 http://119.45.35.97:8080 查看版本"
