# 生产部署基线

该目录提供单台中国大陆云服务器的首发部署方案：Caddy 自动 HTTPS、FastAPI、MySQL 8.4 LTS 和 Redis 限流。API、数据库和 Redis 不直接暴露到公网，公网只开放 80/443。

## 上线前置条件

1. 购买中国大陆云服务器并完成实名认证。
2. 购买域名并完成 ICP 备案；将 API 子域名解析到服务器公网 IP。
3. 在微信公众平台配置 `request` 和 `uploadFile` 合法域名，必须使用备案后的 HTTPS 域名。
4. 获取微信 AppSecret 和 AI 服务 API Key。
5. 服务器安装 Docker Engine 与 Compose 插件，安全组仅开放 22、80、443。

## 首次部署

```bash
cp .env.deploy.example .env.deploy
# 编辑 .env.deploy，所有密码使用强随机值，DATABASE_URL 中的密码需要 URL 编码
docker compose --env-file .env.deploy config
docker compose --env-file .env.deploy up -d --build
docker compose --env-file .env.deploy ps
curl https://你的API域名/health/ready
```

API 容器每次启动会先执行 `alembic upgrade head`。生产配置不完整、仍开启开发登录、使用 SQLite 或演示数据时，应用会拒绝启动。

## 更新版本

```bash
git pull --ff-only
docker compose --env-file .env.deploy up -d --build
docker compose --env-file .env.deploy ps
```

## 数据备份

每天至少备份一次，并将备份文件及校验文件同步到另一存储位置：

```bash
chmod +x deploy/backup.sh deploy/restore.sh
deploy/backup.sh .env.deploy
```

恢复会先自动创建一个恢复前备份，并要求备份文件位于 `backups/` 且通过 SHA-256 校验：

```bash
deploy/restore.sh backups/food_saver_时间.sql.gz --confirm-restore .env.deploy
```

建议通过系统定时任务每天运行 `deploy/backup.sh`。每月至少在临时数据库执行一次恢复演练，不要只检查备份文件是否存在。

## 日常检查

```bash
docker compose --env-file .env.deploy ps
docker compose --env-file .env.deploy logs --tail=200 api
docker compose --env-file .env.deploy logs --tail=200 caddy
curl -fsS https://你的API域名/health/ready
```

就绪检查同时验证数据库与 Redis。生产环境中任一依赖不可用都会返回 503，容器健康检查会据此阻止流量进入异常实例。依赖漏洞由 GitHub Dependabot 和持续集成审计跟踪。
