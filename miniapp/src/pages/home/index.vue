<template>
  <view class="page">
    <view class="hero">
      <view>
        <text class="hero-kicker">今天也要少一点浪费</text>
        <text class="hero-title">家里的食材，先吃快到期的</text>
      </view>
      <text class="hero-icon">🥬</text>
    </view>

    <view class="stats">
      <view class="stat-card green">
        <text class="stat-number">{{ dashboard.inventory_count }}</text>
        <text class="stat-label">库存批次</text>
      </view>
      <view class="stat-card yellow">
        <text class="stat-number">{{ dashboard.expiring_count + dashboard.today_count }}</text>
        <text class="stat-label">需要优先吃</text>
      </view>
      <view class="stat-card red">
        <text class="stat-number">{{ dashboard.expired_count }}</text>
        <text class="stat-label">已经过期</text>
      </view>
    </view>

    <view class="actions">
      <view class="action" @tap="openForm">
        <text class="action-icon">＋</text>
        <text>录入食材</text>
      </view>
      <view class="action" @tap="openRecipe">
        <text class="action-icon">✦</text>
        <text>生成菜谱</text>
      </view>
    </view>

    <view class="section-head">
      <text class="section-title">临期提醒</text>
      <text class="section-link" @tap="openInventory">查看库存 ›</text>
    </view>

    <view v-if="loading" class="empty">正在加载...</view>
    <ErrorState v-else-if="loadError" :message="loadError" @retry="loadDashboard" />
    <view v-else-if="!dashboard.expiring_items.length" class="card empty">暂无需要处理的食材</view>
    <view v-else class="food-list">
      <view v-for="item in dashboard.expiring_items" :key="item.id" class="food-row card">
        <view class="food-emoji">{{ categoryEmoji(item.category) }}</view>
        <view class="food-main">
          <view class="food-title-row">
            <text class="food-name">{{ item.name }}</text>
            <StatusBadge :status="item.status" :text="item.status_text" />
          </view>
          <text class="food-meta">{{ item.quantity }} {{ item.unit }} · {{ item.location }}</text>
          <text class="food-date">到期日：{{ item.expiry_date || '未设置' }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onShow } from '@dcloudio/uni-app'
import { reactive, ref } from 'vue'
import { api } from '../../api'
import ErrorState from '../../components/ErrorState.vue'
import StatusBadge from '../../components/StatusBadge.vue'

const loading = ref(false)
const loadError = ref('')
const dashboard = reactive({
  inventory_count: 0,
  normal_count: 0,
  expiring_count: 0,
  today_count: 0,
  expired_count: 0,
  expiring_items: [],
})

const emojis = { 蔬菜: '🥬', 水果: '🍎', 蛋奶: '🥚', 肉类: '🥩', 主食: '🍚', 调料: '🧂' }
const categoryEmoji = (category) => emojis[category] || '🥣'

async function loadDashboard() {
  loading.value = true
  loadError.value = ''
  try {
    Object.assign(dashboard, await api.dashboard())
  } catch (error) {
    loadError.value = error.message
  } finally {
    loading.value = false
  }
}

const openForm = () => uni.navigateTo({ url: '/pages/inventory/form' })
const openRecipe = () => uni.switchTab({ url: '/pages/recipe/generate' })
const openInventory = () => uni.switchTab({ url: '/pages/inventory/index' })

onShow(loadDashboard)
</script>

<style scoped>
.hero { display: flex; align-items: center; justify-content: space-between; padding: 34rpx; border-radius: 30rpx; background: linear-gradient(135deg, #2f7d4a, #58a56e); color: #fff; }
.hero-kicker { display: block; font-size: 24rpx; opacity: .82; }
.hero-title { display: block; width: 460rpx; margin-top: 14rpx; font-size: 38rpx; line-height: 1.35; font-weight: 700; }
.hero-icon { font-size: 76rpx; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18rpx; margin-top: 24rpx; }
.stat-card { padding: 24rpx 12rpx; border-radius: 22rpx; text-align: center; }
.stat-card.green { background: #e7f5eb; color: #2f7d4a; }
.stat-card.yellow { background: #fff2cf; color: #986400; }
.stat-card.red { background: #fde5e5; color: #b43a41; }
.stat-number, .stat-label { display: block; }
.stat-number { font-size: 42rpx; font-weight: 700; }
.stat-label { margin-top: 6rpx; font-size: 22rpx; }
.actions { display: grid; grid-template-columns: 1fr 1fr; gap: 20rpx; margin-top: 24rpx; }
.action { display: flex; align-items: center; gap: 18rpx; padding: 26rpx 30rpx; border-radius: 22rpx; background: #fff; font-size: 28rpx; font-weight: 600; }
.action-icon { display: grid; place-items: center; width: 52rpx; height: 52rpx; border-radius: 16rpx; background: #e7f5eb; color: #2f7d4a; font-size: 34rpx; }
.section-head { display: flex; align-items: center; justify-content: space-between; margin: 42rpx 4rpx 20rpx; }
.section-title { font-size: 32rpx; font-weight: 700; }
.section-link { color: #2f7d4a; font-size: 25rpx; }
.food-list { display: flex; flex-direction: column; gap: 18rpx; }
.food-row { display: flex; gap: 22rpx; }
.food-emoji { display: grid; place-items: center; width: 82rpx; height: 82rpx; border-radius: 22rpx; background: #f2f6f2; font-size: 42rpx; }
.food-main { flex: 1; min-width: 0; }
.food-title-row { display: flex; justify-content: space-between; align-items: center; gap: 12rpx; }
.food-name { font-size: 30rpx; font-weight: 650; }
.food-meta, .food-date { display: block; margin-top: 10rpx; font-size: 24rpx; color: #79837c; }
</style>
