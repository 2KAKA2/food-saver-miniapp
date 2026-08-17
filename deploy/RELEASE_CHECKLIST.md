# 正式发布检查清单

## 用户需要准备

- 微信小程序 AppID（可以直接填写到 `manifest.json`）
- 微信小程序 AppSecret（只填写在服务器 `.env.deploy`，不要发到聊天或提交 Git）
- 已实名认证且备案完成的域名
- 一台可运行 Docker 的云服务器
- 智谱 AI API Key
- 已核实的运营主体名称、实际 AI 服务提供方名称和统一的协议生效日期
- 微信公众平台中的服务器域名配置权限
- 微信公众平台客服能力，供用户在“我的”和隐私政策页面联系运营者

## 服务器上线前

1. 将 `.env.deploy.example` 复制为 `.env.deploy`，替换全部占位值。
2. 使用强随机密码，并确保 MySQL、Redis 密码和连接地址一致。
3. 将 `miniapp/.env.production.example` 复制为 `miniapp/.env.production`。
4. 将 `miniapp/src/manifest.json` 的 `mp-weixin.appid` 改为真实 AppID。
5. 在两个环境文件中填写同一个协议版本日期，并在小程序生产配置中填写真实运营主体和 AI 服务方；不得保留占位值。
6. 执行发布体检：

   ```powershell
   .\api\.venv\Scripts\python.exe scripts\release_preflight.py
   docker compose --env-file .env.deploy config --quiet
   ```

7. 启动服务后确认 `/health/live` 和 `/health/ready` 均返回成功；生产环境 `/docs` 和 `/openapi.json` 应不可访问。
8. 在微信公众平台将 `https://API域名` 同时添加为 request 和 uploadFile 合法域名。

## 提审前真机验证

- 新用户微信登录和首次创建家庭
- 邀请、加入、切换家庭及成员权限
- 食材新增、编辑、删除、临期与过期计算
- 图片识别失败时的提示和手动确认
- AI 菜谱生成、降级提示、确认制作和库存扣减
- 重复点击确认制作不会重复扣库存
- 账号注销、用户协议和隐私政策入口
- 弱网、接口超时、登录失效和重新登录
- 不同微信账号之间无法读取彼此家庭数据

## 微信审核材料

- 小程序名称、简介、服务类目和图标
- 隐私保护指引，与应用内隐私政策保持一致
- 隐私保护指引准确列出微信登录标识、用户填写内容、照片、家庭共享、AI 第三方处理和账号注销路径
- 审核体验说明和完整操作路径
- 若审核账号无法直接使用，提供可操作的测试方式
- 页面截图、版本号和本次更新说明
