# MediaCraft 生产环境部署指南

## 🚀 快速部署

### 1. 服务器准备

确保服务器具备以下环境：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv python3-pip git nginx ffmpeg

# CentOS/RHEL
sudo yum install python3 python3-venv python3-pip git nginx ffmpeg
```

### 2. 创建部署用户

```bash
sudo useradd -m -s /bin/bash yhzhu
sudo usermod -aG sudo yhzhu
su - yhzhu
```

### 3. 部署应用

```bash
# 克隆代码
git clone https://github.com/your-username/mediacraft.git
cd mediacraft

# 执行部署脚本
chmod +x deploy_to_production_v2.sh
./deploy_to_production_v2.sh
```

### 4. 配置系统服务（可选）

```bash
# 复制服务文件
sudo cp mediacraft-backend.service /etc/systemd/system/

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable mediacraft-backend
sudo systemctl start mediacraft-backend

# 检查状态
sudo systemctl status mediacraft-backend
```

### 5. 配置 Nginx

```bash
# 复制 Nginx 配置
sudo cp updated_mediacraft_nginx.conf /etc/nginx/sites-available/mediacraft
sudo ln -s /etc/nginx/sites-available/mediacraft /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

## 🔧 配置说明

### 环境变量配置

编辑 `.env.production` 文件：

```bash
# 必须修改的配置
SECRET_KEY=your-super-secure-production-secret-key-change-this
CORS_ORIGINS=https://your-domain.com

# 可选配置
MAX_CONCURRENT_TASKS=3
PROCESSING_TIMEOUT=1800
```

### SSL 证书配置

```bash
# 使用 Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 📊 监控和维护

### 查看日志

```bash
# 应用日志
tail -f /home/yhzhu/mediacraft/data/logs/app.log

# 错误日志
tail -f /home/yhzhu/mediacraft/data/logs/error.log

# 系统服务日志
sudo journalctl -u mediacraft-backend -f
```

### 健康检查

```bash
# API 健康检查
curl http://127.0.0.1:50001/api/system/status

# 清理卡住的任务
cd /home/yhzhu/mediacraft
python3 health_check.py
```

### 重启服务

```bash
# 使用部署脚本重启
cd /home/yhzhu/mediacraft
./deploy_to_production_v2.sh

# 或使用系统服务重启
sudo systemctl restart mediacraft-backend
```

## 🔄 更新部署

### 自动更新

```bash
cd /home/yhzhu/mediacraft
git pull origin master
./deploy_to_production_v2.sh
```

### 回滚

如果部署失败，可以查看备份目录进行回滚：

```bash
# 查看备份
ls /tmp/mediacraft_backup_*

# 手动回滚数据
cp -r /tmp/mediacraft_backup_*/data /home/yhzhu/mediacraft/
```

## ⚡ 性能优化

### 系统优化

```bash
# 增加文件描述符限制
echo "yhzhu soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "yhzhu hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 优化内核参数
echo "net.core.somaxconn = 65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 应用优化

- 调整 `MAX_CONCURRENT_TASKS` 根据服务器性能
- 配置适当的 `PROCESSING_TIMEOUT`
- 定期运行 `health_check.py` 清理任务

## 🔒 安全建议

1. **修改默认密钥**：更改 `.env.production` 中的 `SECRET_KEY`
2. **防火墙配置**：只开放必要端口（80, 443）
3. **定期更新**：保持系统和依赖更新
4. **备份策略**：定期备份 `data` 目录
5. **监控日志**：监控错误日志和异常访问

## 📞 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查日志
   tail -f /home/yhzhu/mediacraft/data/logs/app.log
   
   # 检查端口占用
   lsof -i :50001
   ```

2. **视频处理失败**
   ```bash
   # 检查 FFmpeg
   ffmpeg -version
   
   # 检查权限
   ls -la /home/yhzhu/mediacraft/data/
   ```

3. **API 404 错误**
   ```bash
   # 检查 Nginx 配置
   sudo nginx -t
   
   # 检查 API 服务
   curl http://127.0.0.1:50001/api/system/status
   ```