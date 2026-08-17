# 本地电脑真机联调

当前阶段可以让电脑承担后端服务，手机和电脑连接同一个 Wi-Fi 后进行微信真机联调。这个模式适合开发和课堂演示，不等于公网正式上线：电脑关机、切换网络或手机离开当前局域网后，小程序无法连接服务。

## 1. 准备小程序端地址

在 PowerShell 中查看电脑当前使用网卡的 IPv4 地址，然后从项目根目录执行：

```powershell
.\scripts\prepare_local_wechat.ps1 -LanIp 192.168.1.100 -OperatorName "你的运营者展示名称"
```

把示例地址替换为实际的 `10.x`、`172.16-31.x` 或 `192.168.x` 地址。脚本只生成被 Git 忽略的 `miniapp/.env.local`，不会读取或写入 AppSecret。
若网络变化后需要覆盖已有文件，请确认旧配置不再需要，再在命令末尾增加 `-Force`。

## 2. 配置后端

在 `api/.env` 中确认：

```text
WECHAT_APP_ID=wx30ddd1061d78b551
WECHAT_APP_SECRET=仅在本机填写，不要发到聊天或提交到 Git
ALLOW_DEV_LOGIN=false
ALLOWED_HOSTS=127.0.0.1,localhost,你的电脑局域网IP
```

随后启动后端，并确保监听所有本机网络接口：

```powershell
cd api
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

若 Windows 首次询问网络访问权限，只允许“专用网络”。不要把 8000 端口直接映射到公网。

## 3. 构建与导入

```powershell
cd miniapp
npm run build:mp-weixin
```

在微信开发者工具中导入 `miniapp/dist/build/mp-weixin`。开发阶段可临时关闭“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”，然后用真机调试验证登录、家庭共享、录入和扣减流程。

## 4. 连接中断时的行为

首页和库存页会显示当前家庭上一次成功同步的只读快照，并明确标记同步时间。新增、编辑、删除和菜谱生成不会离线排队，避免多位家庭成员恢复网络后覆盖彼此的数据。退出登录、账号会话失效时，本机家庭缓存会被清除。

## 5. 正式发布前必须替换

面向所有用户发布时，可以把 `VITE_API_BASE_URL` 换成公网 HTTPS 地址并配置合法域名，也可以采用 CloudBase 云托管的 `wx.cloud.callContainer` 无域名方案。两种方式都不能继续使用本地 IP 或关闭域名校验；CloudBase 方案见 `deploy/cloudbase/README.md`。
