# CloudBase 无域名首发部署

该方案面向只发布微信小程序的首版：微信小程序通过 `wx.cloud.callContainer` 调用 CloudBase 云托管中的 FastAPI，业务数据使用同一 CloudBase 环境的 MySQL。无需为小程序 API 单独购买域名。

## 1. 创建云资源

在 CloudBase 控制台完成以下操作，并保证资源处于同一环境和地域：

1. 创建并关联微信小程序 `wx30ddd1061d78b551` 的 CloudBase 环境，记录环境 ID。
2. 开通 MySQL，创建 `food_saver` 数据库和仅具有该库权限的业务账号。
3. 在“云托管”中新建容器服务 `food-saver-api`。
4. 首发将实例规格设为最低可用档，最小实例数设为 `0`，最大实例数设为 `1`。

最大实例数为 1 时，可以使用应用内存限流而暂不购买 Redis。扩容到多个实例前，必须接入同地域、同 VPC 的 Redis，并设置 `REQUIRE_REDIS=true`。

## 2. 配置云托管版本

云托管版本使用以下参数：

- 构建方式：上传代码包并通过 Dockerfile 构建。
- Dockerfile：代码包根目录下的 `Dockerfile`。
- 监听端口：`8000`。
- 健康检查路径：`/health/ready`。
- 流量：首次验证成功后再切换为 100%。

从项目根目录制作后端代码包：

```powershell
git archive --format=zip --output food-saver-api-cloudbase.zip HEAD:api
```

该命令只打包 Git 已提交的 `api` 目录，不会包含 `.env`、本地数据库和虚拟环境。将生成的 `food-saver-api-cloudbase.zip` 上传到云托管。

## 3. 填写服务端环境变量

参照 `deploy/cloudbase/api.env.example` 在云托管版本页面逐项填写。以下内容必须由账号持有人在控制台中填写，不能放进代码仓库：

- `DATABASE_URL`：CloudBase MySQL 的内网连接地址；密码中的特殊字符需要 URL 编码。
- `WECHAT_APP_SECRET`：微信公众平台中的小程序 AppSecret。
- `ZHIPU_API_KEY`：可选；不填写时菜谱与识图返回备用结果。

首发保持：

```text
REQUIRE_REDIS=false
REQUIRE_AI_KEY=false
ALLOW_DEV_LOGIN=false
SEED_DEMO_DATA=false
```

如果云托管实际服务名不是 `food-saver-api`，同时修改 `ALLOWED_HOSTS` 和小程序的 `VITE_CLOUDBASE_SERVICE`。

容器启动时会自动执行 `alembic upgrade head`，随后启动 FastAPI。部署日志出现 `生产配置校验失败` 时，应修正环境变量，不要通过关闭生产模式绕过检查。

## 4. 验证后端

在 CloudBase 控制台检查：

1. 构建和部署均成功。
2. `/health/live` 返回 `status: ok`。
3. `/health/ready` 返回数据库 `ok`，Redis 可显示 `disabled`。
4. 容器日志中没有数据库连接、迁移或微信配置错误。

## 5. 构建小程序

复制 CloudBase 小程序配置模板：

```powershell
Copy-Item miniapp\.env.cloudbase.example miniapp\.env.production
```

在 `miniapp/.env.production` 中填写真实的 CloudBase 环境 ID、云托管服务名和已核实的运营者名称，然后构建：

```powershell
Set-Location miniapp
npm run build:mp-weixin
```

微信开发者工具导入 `miniapp/dist/build/mp-weixin`。代码启动时会初始化指定的 CloudBase 环境，普通 JSON 请求使用 `callContainer`，拍照识别会将压缩图片编码后提交给专用接口。

## 6. 上线前验证

至少完成以下流程：

1. 新微信用户首次登录并自动创建个人家庭。
2. 创建家庭、生成邀请码，另一名用户加入并看到同一库存。
3. 手动录入、编辑和删除食材。
4. 拍照识别成功返回候选，未确认前库存不变化。
5. 生成菜谱并确认制作，库存正确扣减。
6. 库存不足时整次扣减失败，数据不发生部分变化。
7. 无 AI 密钥时页面明确显示备用结果，但其他流程仍可完成。
8. 云托管缩容后重新访问，确认冷启动能够正常恢复。

完成体验版验证后，再在微信公众平台完成小程序备案、服务类目、隐私保护指引和版本审核。
