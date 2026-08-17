<template>
  <view class="page">
    <view class="search-row">
      <input v-model="keyword" class="search" placeholder="搜索食材" confirm-type="search" @confirm="load" />
      <button class="add-button" @tap="openForm()">＋</button>
    </view>

    <scroll-view scroll-x class="tabs">
      <view class="tabs-inner">
        <text v-for="tab in tabs" :key="tab.value" class="tab" :class="{ active: filter === tab.value }" @tap="changeFilter(tab.value)">{{ tab.label }}</text>
      </view>
    </scroll-view>

    <OfflineSnapshot v-if="store.usingCache" :saved-at="store.cachedAt" />

    <view v-if="store.loading" class="empty">正在加载...</view>
    <ErrorState v-else-if="loadError" :message="loadError" @retry="load" />
    <view v-else-if="!store.items.length" class="card empty">没有符合条件的食材</view>
    <view v-else class="inventory-list">
      <view v-for="item in store.items" :key="item.id" class="inventory-card card">
        <view class="top-row">
          <view>
            <text class="name">{{ item.name }}</text>
            <text class="category">{{ item.category }} · {{ item.location }}</text>
          </view>
          <StatusBadge :status="item.status" :text="item.status_text" />
        </view>
        <view class="quantity-row">
          <text class="quantity">{{ item.quantity }} <text class="unit">{{ item.unit }}</text></text>
          <text class="expiry">{{ expiryText(item) }}</text>
        </view>
        <view class="card-actions" :class="{ disabled: store.usingCache }">
          <text @tap="openForm(item.id)">编辑</text>
          <text class="danger" @tap="remove(item)">删除</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { api } from '../../api'
import ErrorState from '../../components/ErrorState.vue'
import OfflineSnapshot from '../../components/OfflineSnapshot.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import { useInventoryStore } from '../../stores/inventory'

const store = useInventoryStore()
const keyword = ref('')
const filter = ref('')
const loadError = ref('')
const tabs = [
  { label: '全部', value: '' },
  { label: '临期', value: 'expiring' },
  { label: '今日到期', value: 'today' },
  { label: '已过期', value: 'expired' },
]

async function load() {
  loadError.value = ''
  try {
    await store.load({ status: filter.value, keyword: keyword.value })
  } catch (error) {
    loadError.value = error.message
  }
}

function changeFilter(value) {
  filter.value = value
  load()
}

const openForm = (id) => {
  if (store.usingCache) {
    uni.showToast({ title: '连接电脑服务后才能操作', icon: 'none' })
    return
  }
  uni.navigateTo({ url: `/pages/inventory/form${id ? `?id=${id}` : ''}` })
}
const expiryText = (item) => {
  if (!item.expiry_date) return '未设置到期日'
  if (item.status === 'expired') return `已过期 ${Math.abs(item.days_remaining)} 天`
  if (item.status === 'today') return '今天到期'
  return `${item.days_remaining} 天后到期`
}

function remove(item) {
  if (store.usingCache) {
    uni.showToast({ title: '连接电脑服务后才能删除', icon: 'none' })
    return
  }
  uni.showModal({
    title: '删除食材',
    content: `确定删除“${item.name}”这一批库存吗？`,
    success: async ({ confirm }) => {
      if (!confirm) return
      try {
        await api.deleteInventory(item.id)
        uni.showToast({ title: '已删除' })
        load()
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none' })
      }
    },
  })
}

onShow(load)
</script>

<style scoped>
.search-row { display: flex; gap: 16rpx; }
.search { flex: 1; height: 80rpx; padding: 0 28rpx; border-radius: 40rpx; background: #fff; font-size: 28rpx; }
.add-button { width: 80rpx; height: 80rpx; line-height: 76rpx; padding: 0; border-radius: 50%; background: #2f7d4a; color: #fff; font-size: 44rpx; }
.tabs { margin: 28rpx 0 24rpx; white-space: nowrap; }
.tabs-inner { display: inline-flex; gap: 16rpx; }
.tab { padding: 16rpx 28rpx; border-radius: 999rpx; background: #fff; color: #69736c; font-size: 25rpx; }
.tab.active { background: #2f7d4a; color: #fff; }
.inventory-list { display: flex; flex-direction: column; gap: 20rpx; }
.top-row, .quantity-row, .card-actions { display: flex; justify-content: space-between; align-items: center; }
.name { display: block; font-size: 32rpx; font-weight: 700; }
.category { display: block; margin-top: 8rpx; color: #8a938c; font-size: 23rpx; }
.quantity-row { margin-top: 28rpx; }
.quantity { font-size: 38rpx; font-weight: 700; color: #2f7d4a; }
.unit { font-size: 24rpx; font-weight: 400; }
.expiry { color: #7d877f; font-size: 24rpx; }
.card-actions { justify-content: flex-end; gap: 38rpx; margin-top: 28rpx; padding-top: 20rpx; border-top: 1rpx solid #edf0ed; color: #2f7d4a; font-size: 25rpx; }
.card-actions.disabled { opacity: .45; }
.danger { color: #c34249; }
</style>
