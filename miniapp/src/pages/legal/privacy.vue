<template>
  <view class="legal-page">
    <text class="title">食尽其用隐私政策</text>
    <text class="date">更新日期：{{ LEGAL_DATE_LABEL }}</text>

    <view class="section">
      <text class="heading">一、运营者</text>
      <text class="paragraph">本服务的个人信息处理者为{{ OPERATOR_NAME }}。我们遵循最小必要原则处理你的信息，不使用 DCloud uniStatistics 或其他第三方页面统计服务。</text>
    </view>

    <view class="section">
      <text class="heading">二、我们收集的信息</text>
      <text class="paragraph">为完成登录，我们通过微信登录获得用于识别账号的 OpenID，并记录你同意的协议版本与时间。我们不会读取你的微信昵称或头像；你可以自行设置仅供家庭成员相互识别的显示昵称。为提供核心服务，我们保存你录入的食材名称、数量、存放位置、保质期、菜谱、家庭成员关系和库存变更记录。为保障安全与排查故障，服务器还会处理访问时间、IP 地址、请求状态和客户端基础信息等必要日志。</text>
    </view>
    <view class="section">
      <text class="heading">三、图片与人工智能服务</text>
      <text class="paragraph">只有在你主动选择拍照识别或生成菜谱时，我们才会把相关图片、库存食材和偏好发送给{{ AI_PROVIDER_NAME }}完成识别或菜谱生成。我们的服务器不会持久保存识别原图，识别结果必须经你确认后才会加入库存。我们不会将这些信息用于广告或出售，并会在微信小程序隐私保护指引中同步披露第三方处理情况。</text>
    </view>
    <view class="section">
      <text class="heading">四、家庭共享</text>
      <text class="paragraph">加入同一家庭后，家庭成员可以查看和修改该家庭的食材库存、菜谱和消耗记录。请只邀请你信任的人。家庭所有者可以移除成员，成员退出后不再具有访问权限。</text>
    </view>
    <view class="section">
      <text class="heading">五、存储、安全与保存期限</text>
      <text class="paragraph">我们采用访问令牌哈希、家庭权限校验、传输加密、上传限制、日志脱敏、日志轮转和数据库备份等措施保护信息。正式服务的数据存储在中国大陆境内云服务区域。账号存续期间保存核心业务数据；注销后立即停止账号访问并删除或匿名化在线数据，备份副本按既定轮转周期覆盖，法律法规另有要求的除外。</text>
    </view>
    <view class="section">
      <text class="heading">六、你的权利</text>
      <text class="paragraph">你可以在小程序中查看和修改资料、退出家庭或注销账号。注销后，个人家庭数据和可识别个人资料将被删除或匿名化；多人家庭所有者需要先转让所有者，以保护其他成员的共享数据。</text>
    </view>
    <view class="section">
      <text class="heading">七、联系我们</text>
      <text class="paragraph">如对个人信息处理有疑问，可点击下方按钮通过微信客服联系{{ OPERATOR_NAME }}。</text>
      <button class="contact-button" open-type="contact">联系运营者</button>
    </view>
  </view>
</template>

<script setup>
import { AI_PROVIDER_NAME, LEGAL_DATE_LABEL, OPERATOR_NAME } from '../../config/legal'
</script>

<style scoped>
.legal-page { min-height: 100vh; padding: 36rpx 34rpx 70rpx; background: #fff; }
.title, .date, .heading, .paragraph { display: block; }
.title { font-size: 38rpx; font-weight: 800; color: #243229; }
.date { margin-top: 12rpx; color: #8b948e; font-size: 22rpx; }
.section { margin-top: 36rpx; }
.heading { font-size: 29rpx; font-weight: 700; }
.paragraph { margin-top: 14rpx; color: #526058; font-size: 26rpx; line-height: 1.9; text-align: justify; }
.contact-button { margin-top: 24rpx; background: #e7f5eb; color: #2f7d4a; font-size: 26rpx; }
</style>
