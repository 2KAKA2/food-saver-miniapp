<template>
  <view class="login-page">
    <view class="brand">
      <view class="logo">🥬</view>
      <text class="title">食尽其用</text>
      <text class="subtitle">和家人一起管理食材，优先吃掉快过期的</text>
    </view>

    <view class="feature-list">
      <view class="feature"><text>✓</text><text>家庭成员共享同一份库存</text></view>
      <view class="feature"><text>✓</text><text>临期食材及时提醒</text></view>
      <view class="feature"><text>✓</text><text>根据现有食材生成菜谱</text></view>
    </view>

    <view class="login-area">
      <view class="agreement">
        <checkbox :checked="agreed" color="#2f7d4a" @tap="agreed = !agreed" />
        <text @tap="agreed = !agreed">我已阅读并同意</text>
        <text class="legal-link" @tap="openLegal('agreement')">《用户协议》</text>
        <text>和</text>
        <text class="legal-link" @tap="openLegal('privacy')">《隐私政策》</text>
      </view>
      <button class="primary-button" :loading="loading" @tap="startLogin">
        {{ authMode === 'dev' ? '进入本地体验' : '微信快捷登录' }}
      </button>
      <text v-if="authMode === 'dev'" class="dev-tip">当前为开发登录模式，正式发布时将切换为微信登录</text>
    </view>
  </view>
</template>

<script setup>
import { onLoad } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { AUTH_MODE, useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const agreed = ref(false)
const authMode = AUTH_MODE
const openLegal = (type) => uni.navigateTo({ url: `/pages/legal/${type}` })

async function startLogin() {
  if (!agreed.value) {
    uni.showToast({ title: '请先同意用户协议和隐私政策', icon: 'none' })
    return
  }
  loading.value = true
  try {
    let profile = {}
    if (AUTH_MODE === 'wechat' && typeof uni.getUserProfile === 'function') {
      try {
        const result = await new Promise((resolve, reject) => {
          uni.getUserProfile({ desc: '用于家庭成员识别', success: resolve, fail: reject })
        })
        profile = {
          nickname: result.userInfo?.nickName,
          avatarUrl: result.userInfo?.avatarUrl,
        }
      } catch (_) {
        // 用户拒绝头像昵称时仍可使用默认资料登录。
      }
    }
    await auth.login(profile)
    uni.switchTab({ url: '/pages/home/index' })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none', duration: 2500 })
  } finally {
    loading.value = false
  }
}

onLoad(async () => {
  loading.value = true
  const restored = await auth.refresh()
  loading.value = false
  if (restored) uni.switchTab({ url: '/pages/home/index' })
})
</script>

<style scoped>
.login-page { min-height: 100vh; padding: 130rpx 54rpx 60rpx; background: linear-gradient(180deg, #eef8f0 0%, #f9fbf8 48%, #fff 100%); }
.brand { text-align: center; }
.logo { display: grid; place-items: center; width: 150rpx; height: 150rpx; margin: 0 auto; border-radius: 42rpx; background: #2f7d4a; box-shadow: 0 20rpx 40rpx rgba(47,125,74,.22); font-size: 82rpx; }
.title, .subtitle { display: block; }
.title { margin-top: 34rpx; color: #244e31; font-size: 50rpx; font-weight: 800; }
.subtitle { width: 520rpx; margin: 20rpx auto 0; color: #708078; font-size: 27rpx; line-height: 1.65; }
.feature-list { margin: 80rpx 40rpx 0; }
.feature { display: flex; align-items: center; gap: 20rpx; margin-top: 24rpx; color: #4a5d50; font-size: 27rpx; }
.feature text:first-child { display: grid; place-items: center; width: 40rpx; height: 40rpx; border-radius: 50%; background: #dff1e4; color: #2f7d4a; font-weight: 700; }
.login-area { margin-top: 100rpx; }
.agreement { display: flex; align-items: center; justify-content: center; gap: 8rpx; margin-bottom: 28rpx; color: #7c8780; font-size: 22rpx; }
.agreement checkbox { transform: scale(.75); }
.legal-link { color: #2f7d4a; }
.dev-tip { display: block; margin-top: 22rpx; text-align: center; color: #9aa29d; font-size: 21rpx; }
</style>
