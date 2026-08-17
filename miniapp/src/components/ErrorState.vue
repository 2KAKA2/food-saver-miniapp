<template>
  <view class="error-state card">
    <text class="error-title">暂时没有加载成功</text>
    <text class="error-message">{{ message || '请检查网络后重试' }}</text>
    <button class="retry-button" @tap="$emit('retry')">重新加载</button>
  </view>
</template>

<script setup>
defineProps({ message: { type: String, default: '' } })
defineEmits(['retry'])
</script>

<style scoped>
.error-state { padding: 44rpx 28rpx; text-align: center; }
.error-title, .error-message { display: block; }
.error-title { color: #35443a; font-size: 28rpx; font-weight: 700; }
.error-message { margin-top: 12rpx; color: #879188; font-size: 23rpx; line-height: 1.5; }
.retry-button { width: 220rpx; height: 68rpx; line-height: 68rpx; margin-top: 24rpx; border-radius: 34rpx; background: #e7f5eb; color: #2f7d4a; font-size: 25rpx; }
</style>
