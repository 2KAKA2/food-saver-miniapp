# 食尽其用：AI 家庭食材库存与菜谱生成助手

一个正在按正式发布标准建设的家庭食材管理微信小程序。用户可以通过手机录入食材、查看临期提醒、拍照识别食材，并根据现有库存生成菜谱；确认制作后，系统会自动扣减对应库存。

## 已实现功能

- 首页库存统计、临期和过期提醒
- 微信登录服务端换取身份，客户端不保存或接触微信 AppSecret
- 多家庭空间、家庭切换、邀请码加入与成员权限管理
- 食材批次的新增、编辑、搜索、筛选和删除
- 常用食材快捷录入与图片识别候选
- 按人数、口味和时间生成 AI 菜谱
- 未配置 AI 或调用失败时自动返回可演示的降级结果
- 菜谱历史、详情和实际用量确认
- 制作菜谱后事务化扣减库存并保存变更记录
- 确认制作接口支持幂等重试，避免重复扣减库存
- Redis 分布式限流保护微信登录与 AI 接口
- 账号注销、个人资料匿名化、用户协议和隐私政策页面
- 服务端记录用户同意的协议版本和时间，前后端版本不一致时拒绝登录
- 生产环境关闭交互式接口文档，容器日志与数据库备份自动轮转
- H5 与微信小程序双端构建

## 项目结构

```text
食尽其用-AI食材库存助手/
├── api/       FastAPI + SQLAlchemy 后端
└── miniapp/   uni-app + Vue3 + Pinia 小程序
```

## 启动后端

在 PowerShell 中进入 `api` 目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后可访问：

- 接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

默认使用 `api/data/food_inventory.db`。数据库结构统一由 Alembic 管理，每次更新代码后应先执行 `python -m alembic upgrade head`。需要 MySQL 时，将 `.env` 中的 `DATABASE_URL` 改为：

```text
mysql+pymysql://用户名:密码@127.0.0.1:3306/数据库名?charset=utf8mb4
```

## 配置智谱 AI

编辑 `api/.env`：

```text
ZHIPU_API_KEY=你的智谱APIKey
ZHIPU_CHAT_MODEL=glm-4.7-flash
ZHIPU_VISION_MODEL=glm-4.6v-flash
```

不要把 `.env` 提交到 Git。未配置密钥、网络异常或模型输出不合法时，后端会自动使用演示菜谱或演示识别结果，并在响应中返回 `source: "fallback"`。

## 配置微信登录

微信登录采用“小程序 `uni.login` 获取一次性 code，后端调用微信 `code2session`”的方式。AppSecret 只能配置在后端：

```text
WECHAT_APP_ID=你的小程序AppID
WECHAT_APP_SECRET=你的小程序AppSecret
ALLOW_DEV_LOGIN=false
SEED_DEMO_DATA=false
```

同时将 `miniapp/src/manifest.json` 中 `mp-weixin.appid` 替换为同一个 AppID，并在正式构建使用的环境文件中设置：

```text
VITE_AUTH_MODE=wechat
VITE_API_BASE_URL=https://你的备案域名/api/v1
VITE_LEGAL_VERSION=正式发布日期
VITE_OPERATOR_NAME=已核实的运营主体名称
VITE_AI_PROVIDER_NAME=实际使用的AI服务提供方名称
```

本地开发可以保留 `ALLOW_DEV_LOGIN=true` 和 `VITE_AUTH_MODE=dev`，但生产服务器必须关闭开发登录。开发登录密钥只用于本机联调，不能用于正式环境。

## 运行手机端网页

另开一个 PowerShell，进入 `miniapp` 目录：

```powershell
npm install
Copy-Item .env.example .env
npm run dev:h5
```

浏览器访问终端显示的地址即可。默认后端地址是 `http://127.0.0.1:8000/api/v1`。

## 运行微信小程序

```powershell
npm run build:mp-weixin
```

打开微信开发者工具，导入以下目录：

```text
miniapp/dist/build/mp-weixin
```

当前代码仍使用测试 AppID，但正式域名校验已开启。使用本地真机调试时可在微信开发者工具中临时关闭域名校验：

1. 确保手机和电脑连接同一局域网。
2. 查询电脑局域网 IPv4 地址。
3. 将 `miniapp/.env` 中的地址改为 `http://电脑局域网IP:8000/api/v1`。
4. 重新执行 `npm run build:mp-weixin`。
5. 确保 Windows 防火墙允许后端的 8000 端口访问；不要把关闭域名校验的设置用于正式体验版。

正式上线时仍需配置真实微信 AppID、HTTPS 服务器和微信小程序合法域名。

## 家庭共享与权限

- 用户首次登录时自动创建个人家庭。
- 用户可以创建多个家庭，并在“我的”页面切换当前家庭。
- 只有家庭所有者可以生成邀请码、移除成员或转让所有者。
- 邀请码默认 24 小时有效且只能使用一次，服务端仅保存邀请码哈希。
- 所有库存、菜谱和变更记录都绑定家庭；后端会校验成员关系，客户端修改家庭编号不能越权读取数据。

## 测试与构建

后端测试：

```powershell
cd api
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

前端构建：

```powershell
cd miniapp
npm run build:h5
npm run build:mp-weixin
..\api\.venv\Scripts\python.exe ..\scripts\check_npm_audit.py --cwd .
```

仓库包含 GitHub Actions 自动检查，会在推送和合并请求时执行后端测试、数据库迁移校验、H5/微信小程序构建和部署模板检查。

正式发布前，复制并填写 `.env.deploy` 与 `miniapp/.env.production`，再从项目根目录执行：

```powershell
.\api\.venv\Scripts\python.exe scripts\release_preflight.py
docker compose --env-file .env.deploy config --quiet
```

该检查不会输出密钥内容，只会列出缺失、仍为占位值或互相不一致的配置项。

## 生产部署

生产部署基线位于 `deploy/`，使用 Caddy 自动 HTTPS、FastAPI、MySQL 8.4 LTS 和 Redis。执行前需要准备备案域名、云服务器、微信 AppSecret 和 AI API Key，具体步骤见 `deploy/README.md`。

从云资源准备到微信提审的逐项清单见 `deploy/RELEASE_CHECKLIST.md`，可直接整理到微信公众平台的材料草案见 `docs/WECHAT_RELEASE_MATERIALS.md`。

当前已验证能力、端到端测试证据和剩余上线条件见 `docs/RELEASE_STATUS.md`。

中国大陆云服务器的配置档位、备案、对象存储与监控方案见 `docs/CLOUD_DEPLOYMENT_OPTIONS.md`。

生产环境会进行启动安全校验：使用 SQLite、缺少 Redis/微信/AI 配置、开启开发登录或演示数据时，API 会拒绝启动。`/health/live` 用于进程存活检查，`/health/ready` 用于数据库就绪检查。

## 推荐演示流程

1. 首页展示西红柿和牛奶临期提醒。
2. 使用快捷录入或拍照识别添加一个新食材。
3. 在库存页查看不同批次和保质期状态。
4. 进入 AI 菜谱页选择食材并生成菜谱。
5. 在菜谱详情中修改实际用量并确认制作。
6. 返回库存页展示数量已经扣减，再到历史页查看已制作状态。
