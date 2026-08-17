# 食尽其用项目运行指令手册

适用环境：Windows 10/11、PowerShell、Python 3.12、Node.js 20、微信开发者工具。CloudBase 部署和传统 Docker 部署按需使用。

## 0. 设置项目路径

每次新开 PowerShell 后，先执行：

```powershell
$ProjectRoot = 'D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手'
```

## 1. 日常快速启动

### 1.1 启动后端

打开第一个 PowerShell：

```powershell
$ProjectRoot = 'D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手'
Set-Location "$ProjectRoot\api"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问地址：

- 接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

停止后端：在运行窗口按 `Ctrl+C`。

### 1.2 构建本地微信小程序

```powershell
$ProjectRoot = 'D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手'
Set-Location "$ProjectRoot\miniapp"
$env:VITE_API_TRANSPORT = 'http'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
npm run build:mp-weixin
Remove-Item Env:VITE_API_TRANSPORT
Remove-Item Env:VITE_API_BASE_URL
```

微信开发者工具导入目录：

```text
D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手\miniapp\dist\build\mp-weixin
```

## 2. 本地首次安装

### 2.1 安装后端

```powershell
$ProjectRoot = 'D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手'
Set-Location "$ProjectRoot\api"

if (-not (Test-Path '.venv')) {
    py -3.12 -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
}

.\.venv\Scripts\python.exe -m alembic upgrade head
```

已有 `api/.env` 时不要用示例文件覆盖，否则可能丢失当前本地配置。

### 2.2 安装前端

```powershell
Set-Location "$ProjectRoot\miniapp"
npm ci

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
}
```

## 3. 手机真机连接本地电脑

### 3.1 查询电脑局域网地址

```powershell
ipconfig
```

找到无线网卡下类似 `192.168.1.100` 的 IPv4 地址。

### 3.2 生成真机配置

将示例 IP 换成电脑的实际地址：

```powershell
$ProjectRoot = 'D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手'
Set-Location $ProjectRoot
.\scripts\prepare_local_wechat.ps1 -LanIp 192.168.1.100
```

如果 `miniapp/.env.local` 已存在并确认需要覆盖：

```powershell
.\scripts\prepare_local_wechat.ps1 -LanIp 192.168.1.100 -Force
```

### 3.3 配置本地微信登录

```powershell
notepad "$ProjectRoot\api\.env"
```

确认私密配置中包含：

```text
WECHAT_APP_ID=wx30ddd1061d78b551
WECHAT_APP_SECRET=你的微信AppSecret
ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.100
```

不要把 AppSecret 发到聊天中或提交到 Git。

### 3.4 构建真机版本

```powershell
Set-Location "$ProjectRoot\miniapp"
npm run build:mp-weixin
```

随后在微信开发者工具中重新编译，并在开发阶段临时关闭域名校验。手机和电脑必须连接同一个 Wi-Fi，后端必须使用 `--host 0.0.0.0` 启动。

## 4. 完整测试

### 4.1 后端

```powershell
$ProjectRoot = 'D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手'
Set-Location "$ProjectRoot\api"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

### 4.2 前端

```powershell
Set-Location "$ProjectRoot\miniapp"
npm run build:mp-weixin
..\api\.venv\Scripts\python.exe ..\scripts\check_npm_audit.py --cwd .
```

### 4.3 CloudBase 编译通道

下面只验证 CloudBase 代码能否编译，不会连接真实环境：

```powershell
Set-Location "$ProjectRoot\miniapp"
$env:VITE_API_TRANSPORT = 'cloudbase'
$env:VITE_CLOUDBASE_ENV_ID = 'test-env-id'
$env:VITE_CLOUDBASE_SERVICE = 'food-saver-api'
$env:VITE_AUTH_MODE = 'wechat'
npm run build:mp-weixin
Remove-Item Env:VITE_API_TRANSPORT
Remove-Item Env:VITE_CLOUDBASE_ENV_ID
Remove-Item Env:VITE_CLOUDBASE_SERVICE
Remove-Item Env:VITE_AUTH_MODE
```

测试结束后，若要继续本地运行，请重新执行第 1.2 节的本地微信小程序构建指令。

## 5. CloudBase 正式小程序

### 5.1 创建前端正式配置

```powershell
$ProjectRoot = 'D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手'
Set-Location "$ProjectRoot\miniapp"

if (-not (Test-Path '.env.production')) {
    Copy-Item '.env.cloudbase.example' '.env.production'
}

notepad '.env.production'
```

需要填写：

```text
VITE_API_TRANSPORT=cloudbase
VITE_CLOUDBASE_ENV_ID=你的CloudBase环境ID
VITE_CLOUDBASE_SERVICE=food-saver-api
VITE_AUTH_MODE=wechat
VITE_LEGAL_VERSION=2026-08-17
VITE_OPERATOR_NAME=微信公众平台显示的真实运营者名称
VITE_AI_PROVIDER_NAME=北京智谱华章科技有限公司（智谱AI）
```

### 5.2 构建正式小程序

```powershell
Set-Location "$ProjectRoot\miniapp"
npm run build:mp-weixin
```

将 `miniapp/dist/build/mp-weixin` 导入微信开发者工具。

### 5.3 生成后端上传包

`git archive` 只包含已经提交的代码，因此应先确认 Git 状态：

```powershell
Set-Location $ProjectRoot
git status
git log -1 --oneline
git archive --format=zip --output food-saver-api-cloudbase.zip HEAD:api
```

上传包位置：

```text
D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手\food-saver-api-cloudbase.zip
```

CloudBase 云托管参数：

```text
服务名称：food-saver-api
Dockerfile：Dockerfile
监听端口：8000
健康检查：/health/ready
最小实例数：0
最大实例数：1
```

### 5.4 检查 CloudBase 模板

```powershell
Set-Location $ProjectRoot
.\api\.venv\Scripts\python.exe scripts\release_preflight.py `
    --deploy-env deploy\cloudbase\api.env.example `
    --miniapp-env miniapp\.env.cloudbase.example `
    --template
```

真实的 MySQL 密码、微信 AppSecret 和 AI Key 只填写在 CloudBase 控制台环境变量中，不要写入示例文件。

## 6. Docker 镜像检查

先启动 Docker Desktop，然后执行：

```powershell
$ProjectRoot = 'D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手'
Set-Location $ProjectRoot
docker build --tag food-saver-api:local .\api
docker images food-saver-api
```

## 7. 传统 Docker Compose 部署

本节只用于带域名的独立服务器方案，CloudBase 首版不需要执行。

### 7.1 创建配置

```powershell
Set-Location $ProjectRoot

if (-not (Test-Path '.env.deploy')) {
    Copy-Item '.env.deploy.example' '.env.deploy'
}

notepad '.env.deploy'
```

### 7.2 检查和启动

```powershell
docker compose --env-file .env.deploy config --quiet
docker compose --env-file .env.deploy up -d --build
docker compose --env-file .env.deploy ps
```

### 7.3 查看日志

```powershell
docker compose --env-file .env.deploy logs --tail=200 api
docker compose --env-file .env.deploy logs --tail=200 caddy
```

### 7.4 停止服务

```powershell
docker compose --env-file .env.deploy down
```

不要随意增加 `-v`，否则会同时删除数据库卷。

## 8. Git 常用指令

### 8.1 查看状态

```powershell
$ProjectRoot = 'D:\1_1study_homework\企业实训\食尽其用-AI食材库存助手'
Set-Location $ProjectRoot
git status
git branch --show-current
git log -5 --oneline
```

### 8.2 使用 CloudBase 功能分支

```powershell
git switch feat/cloudbase-deployment
git pull --ff-only
```

### 8.3 推送已经提交的代码

```powershell
git push
```

## 9. 常见问题

### 后端提示端口已被占用

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

关闭旧后端窗口后重新启动，不要直接结束不确定用途的系统进程。

### 真机无法连接电脑

确认：

1. 手机和电脑连接同一个 Wi-Fi。
2. 使用电脑局域网 IPv4，而不是 `127.0.0.1`。
3. Windows 防火墙允许 Python 或 8000 端口访问。
4. 后端以 `--host 0.0.0.0` 启动。

### 当前构建到底是本地版还是 CloudBase 版

- `VITE_API_TRANSPORT=http`：本地或普通 HTTPS API。
- `VITE_API_TRANSPORT=cloudbase`：CloudBase `callContainer`。
- 每次切换配置后必须重新执行 `npm run build:mp-weixin`。
