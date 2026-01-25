# Sub2API v0.1.62 GitHub URL 更新验证指南

## ✅ 已完成的工作

### 1. GitHub Release 创建 ✅
- **Release URL**: https://github.com/lairulan/sub2api/releases/tag/v0.1.62
- **版本**: v0.1.62
- **二进制文件**: sub2api_linux_amd64 (已上传)
- **发布时间**: 2026-01-25

### 2. 代码修改 ✅
- 前端: AppHeader.vue, HomeView.vue
- 后端: update_service.go
- 所有 GitHub URL 已更新为 lairulan/sub2api

### 3. 服务器部署 ✅
- 服务器: 119.45.35.97
- 服务状态: Active (running)
- MD5: d2915093be67bc3b28ca1f8db223e44a

---

## 🔍 如何验证 GitHub 链接已更新

### 方法 1: 清除浏览器缓存（推荐）

网站可能缓存了旧版本的前端代码，需要强制刷新：

#### Chrome/Edge
```
Windows: Ctrl + Shift + Delete
Mac: Command + Shift + Delete

或者:
Windows: Ctrl + F5 (强制刷新)
Mac: Command + Shift + R (强制刷新)
```

#### Firefox
```
Windows: Ctrl + Shift + Delete
Mac: Command + Shift + Delete

或者:
Windows: Ctrl + Shift + R
Mac: Command + Shift + R
```

#### Safari
```
Mac: Command + Option + E (清空缓存)
然后: Command + R (刷新)
```

### 方法 2: 使用无痕/隐私模式

1. 打开浏览器的无痕/隐私窗口
2. 访问: http://relay.0xfaheng.xyz
3. 检查 GitHub 链接

### 方法 3: 禁用缓存（开发者模式）

1. 按 F12 打开开发者工具
2. Network 标签页
3. 勾选 "Disable cache"
4. 刷新页面

---

## 📍 需要检查的位置

### 位置 1: 用户菜单 GitHub 链接
```
步骤:
1. 登录网站
2. 点击右上角用户头像
3. 查看下拉菜单中的 "GitHub" 链接
4. 点击后应该跳转到: https://github.com/lairulan/sub2api
```

### 位置 2: 首页 GitHub 链接
```
步骤:
1. 访问网站首页 (未登录状态)
2. 滚动到页面底部 Footer
3. 点击 "GitHub" 链接
4. 应该跳转到: https://github.com/lairulan/sub2api
```

### 位置 3: 版本检查 "查看发布" 链接
```
步骤:
1. 以管理员身份登录
2. 点击左侧边栏顶部的版本号 "v0.1.62"
3. 点击下拉菜单中的刷新按钮 🔄
4. 点击 "查看发布" 链接
5. 应该跳转到: https://github.com/lairulan/sub2api/releases/tag/v0.1.62
```

---

## 🐛 常见问题

### Q1: 点击"查看发布"还是跳转到旧地址
**原因**: 浏览器缓存了旧的 API 响应或前端代码

**解决方法**:
1. 强制刷新页面 (Ctrl+Shift+R 或 Cmd+Shift+R)
2. 清除浏览器缓存
3. 使用无痕模式访问

### Q2: 版本号显示正确，但链接不对
**原因**: 前端代码更新了，但 API 缓存还在

**解决方法**:
1. 在版本下拉菜单中点击刷新按钮
2. 等待 API 重新从 GitHub 获取最新信息
3. 版本检查 API 有 20 分钟缓存，可能需要等待

### Q3: 所有链接都正确，但版本检查显示 v0.1.61
**原因**: GitHub API 缓存

**解决方法**:
等待几分钟让 GitHub API 缓存过期，或者:
1. 强制刷新版本信息 (点击刷新按钮并勾选 force)
2. 后端会重新调用 GitHub API

---

## 🧪 技术验证

### 验证 GitHub API
```bash
# 检查你的仓库最新 release
curl -s "https://api.github.com/repos/lairulan/sub2api/releases/latest" | grep '"html_url"\|"tag_name"'

# 预期输出:
# "html_url": "https://github.com/lairulan/sub2api/releases/tag/v0.1.62"
# "tag_name": "v0.1.62"
```

### 验证前端资源
```bash
# 检查前端编译时间
ls -lh /Users/rulanlai/sub2api/backend/internal/web/dist/

# 检查是否包含最新代码
grep -r "lairulan" /Users/rulanlai/sub2api/backend/internal/web/dist/assets/
```

### 验证服务器二进制
```bash
# 登录服务器
ssh ubuntu@119.45.35.97

# 检查二进制 MD5
md5sum /opt/sub2api/sub2api
# 预期: d2915093be67bc3b28ca1f8db223e44a

# 检查服务运行时间
sudo systemctl status sub2api | grep Active
# 预期: Active (running) since Sun 2026-01-25 09:32:21
```

---

## ✨ 验证成功标志

当所有以下条件满足时，说明更新成功:

- ✅ 用户菜单中的 GitHub 链接指向 lairulan/sub2api
- ✅ 首页 Footer 的 GitHub 链接指向 lairulan/sub2api
- ✅ 版本检查"查看发布"指向 lairulan/sub2api/releases/tag/v0.1.62
- ✅ 服务器运行的是最新二进制 (MD5: d2915093be67bc3b28ca1f8db223e44a)
- ✅ GitHub Release v0.1.62 已存在并包含二进制文件

---

## 📞 需要帮助？

如果按照上述步骤仍然看到旧链接:

1. **完全清除浏览器数据**
   - 清除 cookies
   - 清除网站数据
   - 清除缓存图像和文件

2. **检查服务器日志**
   ```bash
   ssh ubuntu@119.45.35.97
   sudo journalctl -u sub2api -n 50
   ```

3. **重启浏览器**
   完全关闭浏览器（不是只关标签页），然后重新打开

4. **尝试不同浏览器**
   使用另一个浏览器测试，以确认不是浏览器特定问题

---

**验证指南创建时间**: 2026-01-25 09:40:00 CST
