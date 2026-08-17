# 食尽其用：AI 家庭食材库存与菜谱生成助手

一个面向家庭食材管理的课程演示项目。用户可以通过手机录入食材、查看临期提醒、拍照识别食材，并根据现有库存生成菜谱；确认制作后，系统会自动扣减对应库存。

## 已实现功能

- 首页库存统计、临期和过期提醒
- 食材批次的新增、编辑、搜索、筛选和删除
- 常用食材快捷录入与图片识别候选
- 按人数、口味和时间生成 AI 菜谱
- 未配置 AI 或调用失败时自动返回可演示的降级结果
- 菜谱历史、详情和实际用量确认
- 制作菜谱后事务化扣减库存并保存变更记录
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
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后可访问：

- 接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

默认使用 `api/data/food_inventory.db`，首次启动会自动建表并加入演示食材和菜谱。需要 MySQL 时，将 `.env` 中的 `DATABASE_URL` 改为：

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

当前演示配置使用测试 AppID，并关闭开发阶段域名校验。使用真机调试时：

1. 确保手机和电脑连接同一局域网。
2. 查询电脑局域网 IPv4 地址。
3. 将 `miniapp/.env` 中的地址改为 `http://电脑局域网IP:8000/api/v1`。
4. 重新执行 `npm run build:mp-weixin`。
5. 确保 Windows 防火墙允许后端的 8000 端口访问。

正式上线时仍需配置真实微信 AppID、HTTPS 服务器和微信小程序合法域名。

## 测试与构建

后端测试：

```powershell
cd api
.\.venv\Scripts\python.exe -m pytest -q
```

前端构建：

```powershell
cd miniapp
npm run build:h5
npm run build:mp-weixin
```

## 推荐演示流程

1. 首页展示西红柿和牛奶临期提醒。
2. 使用快捷录入或拍照识别添加一个新食材。
3. 在库存页查看不同批次和保质期状态。
4. 进入 AI 菜谱页选择食材并生成菜谱。
5. 在菜谱详情中修改实际用量并确认制作。
6. 返回库存页展示数量已经扣减，再到历史页查看已制作状态。

