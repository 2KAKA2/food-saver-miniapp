<template>
  <view class="legal-page">
    <text class="title">食尽其用隐私政策</text>
    <text class="date">更新日期：2026年8月17日</text>

    <view class="section">
      <text class="heading">一、我们收集的信息</text>
      <text class="paragraph">为完成登录，我们通过微信登录获得用于识别账号的 OpenID；在你主动授权后，可能使用微信昵称和头像。为提供核心服务，我们保存你录入的食材名称、数量、存放位置、保质期、菜谱、家庭成员关系和库存变更记录。</text>
    </view>
    <view class="section">
      <text class="heading">二、图片与人工智能服务</text>
      <text class="paragraph">只有在你主动选择拍照识别或生成菜谱时，我们才处理相关图片和食材信息。图片可能被发送给已配置的人工智能服务提供方（当前计划使用智谱AI）完成识别；我们不会将图片用于广告或出售。正式上线前会在小程序隐私保护指引中同步披露第三方处理情况。</text>
    </view>
    <view class="section">
      <text class="heading">三、家庭共享</text>
      <text class="paragraph">加入同一家庭后，家庭成员可以查看和修改该家庭的食材库存、菜谱和消耗记录。请只邀请你信任的人。家庭所有者可以移除成员，成员退出后不再具有访问权限。</text>
    </view>
    <view class="section">
      <text class="heading">四、存储与安全</text>
      <text class="paragraph">我们采用访问令牌哈希、家庭权限校验、传输加密、上传限制、日志脱敏和数据库备份等措施保护信息。正式服务的数据存储地点为中国大陆境内云服务区域，保存时间以实现服务所需的最短期限为准。</text>
    </view>
    <view class="section">
      <text class="heading">五、你的权利</text>
      <text class="paragraph">你可以在小程序中查看和修改资料、退出家庭或注销账号。注销后，个人家庭数据和可识别个人资料将被删除或匿名化；多人家庭所有者需要先转让所有者，以保护其他成员的共享数据。</text>
    </view>
    <view class="section">
      <text class="heading">六、联系我们</text>
      <text class="paragraph">如对个人信息处理有疑问，可通过小程序内的微信客服联系运营者。运营主体以微信公众平台展示的信息为准。</text>
    </view>
  </view>
</template>

<style scoped>
.legal-page { min-height: 100vh; padding: 36rpx 34rpx 70rpx; background: #fff; }
.title, .date, .heading, .paragraph { display: block; }
.title { font-size: 38rpx; font-weight: 800; color: #243229; }
.date { margin-top: 12rpx; color: #8b948e; font-size: 22rpx; }
.section { margin-top: 36rpx; }
.heading { font-size: 29rpx; font-weight: 700; }
.paragraph { margin-top: 14rpx; color: #526058; font-size: 26rpx; line-height: 1.9; text-align: justify; }
</style>

