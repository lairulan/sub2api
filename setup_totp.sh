#!/bin/bash
# TOTP 加密密钥配置脚本

echo "================================"
echo "  Sub2API TOTP 配置助手"
echo "================================"
echo ""

# 生成密钥
echo "1️⃣  生成 TOTP 加密密钥..."
TOTP_KEY=$(openssl rand -hex 32)
echo "✅ 密钥已生成: $TOTP_KEY"
echo ""

# 显示配置
echo "2️⃣  请将以下内容添加到服务器的 /opt/sub2api/config.yaml:"
echo ""
echo "---复制以下内容---"
echo "totp:"
echo "  encryption_key: \"$TOTP_KEY\""
echo "---复制结束---"
echo ""

# 保存到本地
echo "3️⃣  密钥已保存到: ./totp_key.txt"
echo "$TOTP_KEY" > totp_key.txt
chmod 600 totp_key.txt
echo ""

# 提供部署命令
echo "4️⃣  部署到服务器的命令:"
echo ""
echo "ssh ubuntu@119.45.35.97"
echo "sudo nano /opt/sub2api/config.yaml"
echo ""
echo "# 添加上述配置后，重启服务:"
echo "sudo systemctl restart sub2api"
echo "sudo systemctl status sub2api"
echo ""

echo "✅ 配置完成！"
echo ""
echo "⚠️  安全提示:"
echo "- 请妥善保管 totp_key.txt 文件"
echo "- 密钥泄露会导致2FA安全失效"
echo "- 不要将密钥提交到版本控制系统"
