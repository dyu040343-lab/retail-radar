#!/bin/bash
# 散户雷达侦探 - 腾讯云香港服务器部署脚本
# 使用方法: bash deploy.sh

set -e

echo "=========================================="
echo "📡 散户雷达侦探 - 部署中..."
echo "=========================================="

# 1. 安装依赖
echo "📦 安装依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip git > /dev/null 2>&1
pip3 install requests --break-system-packages -q 2>/dev/null || sudo pip3 install requests --break-system-packages -q

# 2. 克隆项目
echo "📥 克隆项目..."
cd /home/ubuntu
if [ -d "retail-radar" ]; then
    cd retail-radar
    git pull -q
else
    git clone https://github.com/dyu040343-lab/retail-radar.git
    cd retail-radar
fi

# 3. 首次抓取数据
echo "🔍 抓取数据..."
python3 scripts/fetch_data.py

# 4. 配置定时任务（交易日每小时更新）
echo "⏰ 配置定时任务..."
CRON_JOB="0 1-8 * * 1-5 cd /home/ubuntu/retail-radar && /usr/bin/python3 scripts/fetch_data.py >> /home/ubuntu/retail-radar/cron.log 2>&1"
( crontab -l 2>/dev/null | grep -v "retail-radar" ; echo "$CRON_JOB" ) | crontab -
echo "  ✅ 定时任务已配置: 交易日北京时间 9:00-16:00 每小时更新"

# 5. 创建 systemd 服务（保持Web服务运行）
echo "🚀 配置Web服务..."
sudo tee /etc/systemd/system/retail-radar.service > /dev/null << 'UNIT'
[Unit]
Description=Retail Investor Radar Web Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/retail-radar
ExecStart=/usr/bin/python3 -m http.server 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable retail-radar
sudo systemctl restart retail-radar
echo "  ✅ Web服务已启动 (端口 8080)"

# 6. 检查防火墙
echo "🔥 检查防火墙..."
sudo iptables -C INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null || true

# 7. 获取服务器公网IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "your-server-ip")

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "🌐 访问地址: http://$SERVER_IP:8080/retail-radar.html"
echo ""
echo "📋 服务管理:"
echo "  查看状态: sudo systemctl status retail-radar"
echo "  重启服务: sudo systemctl restart retail-radar"
echo "  查看日志: sudo journalctl -u retail-radar -f"
echo ""
echo "⏰ 定时任务:"
echo "  查看任务: crontab -l"
echo "  查看日志: cat /home/ubuntu/retail-radar/cron.log"
echo ""
echo "⚠️  腾讯云安全组:"
echo "  请在腾讯云控制台 → 轻量应用服务器 → 防火墙"
echo "  添加规则: TCP 8080 端口放行"
echo "=========================================="
