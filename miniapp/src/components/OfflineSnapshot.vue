<template>
  <view class="offline-banner">
    <text class="offline-title">电脑服务暂时无法连接</text>
    <text class="offline-detail">正在显示 {{ formattedTime }} 的库存快照。离线状态只能查看，不能修改。</text>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  savedAt: { type: String, default: '' },
})

const formattedTime = computed(() => {
  if (!props.savedAt) return '上次同步'
  const value = new Date(props.savedAt)
  if (Number.isNaN(value.getTime())) return '上次同步'
  const pad = (part) => String(part).padStart(2, '0')
  return `${value.getMonth() + 1}月${value.getDate()}日 ${pad(value.getHours())}:${pad(value.getMinutes())}`
})
</script>

<style scoped>
.offline-banner { margin: 20rpx 0; padding: 22rpx 26rpx; border: 1rpx solid #efd190; border-radius: 20rpx; background: #fff8e7; color: #78581d; }
.offline-title, .offline-detail { display: block; }
.offline-title { font-size: 26rpx; font-weight: 700; }
.offline-detail { margin-top: 8rpx; font-size: 23rpx; line-height: 1.55; }
</style>
