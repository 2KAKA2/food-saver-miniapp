# 中国大陆云端部署选型

资料核对日期：2026-08-17。价格和活动会变化，最终以下单页为准；本文不代表已经购买或开通任何服务。

## 建议结论

当前已确定首发优先采用 CloudBase：FastAPI 部署到云托管、业务数据使用 CloudBase MySQL、小程序通过 `wx.cloud.callContainer` 调用。该方案无需为纯小程序 API 单独申请域名，且现有 Dockerfile、SQLAlchemy 和 Alembic 可以继续使用。

腾讯云轻量应用服务器上的 Docker Compose 保留为需要 H5、公开 API 或完整自主管理时的备选方案；阿里云轻量服务器同样可以运行该备选架构。

## CloudBase 首发架构

```text
微信小程序
    │ wx.cloud.callContainer
    ▼
CloudBase 云托管：FastAPI
    ├── CloudBase MySQL
    ├── 单实例内存限流（扩容前切换腾讯云 Redis）
    ├── 微信 code2session
    └── 智谱 AI 文本/视觉接口（可选，失败自动降级）
```

具体配置与验证步骤见 `deploy/cloudbase/README.md`。

## 两档配置

### 低成本试运行

- 2 核 CPU、2 GB 内存、40 GB SSD、3 Mbps、200 GB/月流量包。
- 腾讯云官方页面在核对时显示 45 元/月或 459 元/年。
- 适合早期少量家庭使用；必须设置内存和磁盘告警，服务器上不要同时运行开发工具。
- MySQL、Redis、API 和 Caddy 共用一台机器，后续达到资源阈值再升级。

### 推荐正式首发

- 2 核 CPU、4 GB 内存、100 GB SSD、7 Mbps、1000 GB/月流量包。
- 腾讯云官方页面在核对时显示 100 元/月或 1020 元/年。
- 为 MySQL 缓存、Docker 更新和短时并发保留更多余量，正式面向公开用户时更稳妥。

参考：[腾讯云轻量应用服务器规格与价格](https://cloud.tencent.com/product/lighthouse?Is=sdk-topnav)。腾讯云轻量套餐支持升级但不支持降级，因此下单前应结合预算确定档位：[使用限制](https://cloud.tencent.com/document/product/1207/44376)。

阿里云同样提供面向小型应用的轻量服务器，但官方产品页要求在购买页查看实时价格：[阿里云轻量应用服务器](https://cn.aliyun.com/product/swas)。

## 传统服务器备用架构

```text
微信小程序
    │ HTTPS request / uploadFile
    ▼
Caddy（80/443，自动证书）
    ▼
FastAPI（仅容器内 8000）
    ├── MySQL（不开放公网端口）
    ├── Redis（不开放公网端口）
    ├── 微信 code2session
    └── 智谱 AI 文本/视觉接口

每日数据库备份 ──► 私有对象存储桶（服务器外副本）
云监控/外部拨测 ──► 微信或短信告警
```

食材图片只在用户主动识别时临时传给后端和 AI 服务，不长期保存，因此首版对象存储只用于数据库备份，减少隐私数据和存储成本。

## 传统服务器的备案、域名与 HTTPS

- 使用中国内地服务器向公众提供服务需要完成 ICP 备案。腾讯云和阿里云都要求用于备案的轻量服务器累计购买至少 3 个月。
- 建议注册一个普通域名，并使用 `api.你的域名` 作为后端地址。
- Caddy 自动申请和续期 HTTPS 证书，安全组只开放 22、80、443。
- 微信小程序正式环境只连接预先配置的通讯域名；`request` 和 `uploadFile` 均配置同一个 HTTPS API 域名，不能使用公网 IP 或 `localhost`。

参考：[腾讯云轻量服务器备案限制](https://cloud.tencent.com/document/product/1207/44376)、[阿里云轻量服务器备案说明](https://help.aliyun.com/zh/simple-application-server/support/faq)、[微信小程序网络要求](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)。

## 对象存储与备份

- 创建与服务器同地域的私有存储桶，禁止公共读写。
- 每日运行 `deploy/backup.sh`，生成压缩备份和 SHA-256 校验文件。
- 将备份同步到对象存储，保留最近 30 天；每月至少恢复演练一次。
- 数据库本机目录和对象存储不能视为同一份备份，必须保留服务器外副本。
- 腾讯云轻量对象存储支持与 Lighthouse 挂载并用于服务器数据备份；阿里云 OSS 提供标准、低频和归档存储，可用于数据库备份。

参考：[腾讯云轻量对象存储](https://cloud.tencent.com/product/lighthousecos)、[挂载轻量对象存储](https://cloud.tencent.com/document/product/1207/97692)、[阿里云 OSS 数据灾备](https://help.aliyun.com/zh/oss/backup-database-to-oss)。

## 监控与告警基线

上线时至少配置：

- CPU 连续 10 分钟高于 80%。
- 内存连续 5 分钟高于 85%。
- 系统盘使用率高于 80%。
- 公网 `/health/ready` 连续 3 次失败。
- HTTPS 证书剩余时间不足 14 天。
- 最近一次成功备份超过 26 小时。
- Docker 容器反复重启或 MySQL/Redis 健康检查失败。

腾讯云可观测平台支持按阈值持续检测，并通过微信、短信等方式通知：[告警管理](https://cloud.tencent.com/document/product/248/42449)。服务器内部健康检查只能发现进程问题，仍需服务器外部拨测验证公网、DNS 和 HTTPS。

## 需要用户决定

1. 小程序主体类型：个人、个体工商户或企业。
2. 可接受的年度预算。
3. 是否优先使用腾讯云；若已有其他云厂商实名认证账号，应优先复用。

收到决定后再执行购买、实名认证、备案或付费开通操作。
