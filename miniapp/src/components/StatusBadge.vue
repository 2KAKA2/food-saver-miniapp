<template>
  <text class="badge" :class="`badge-${status}`">{{ text }}</text>
</template>

<script setup>
defineProps({
  status: { type: String, default: 'normal' },
  text: { type: String, default: '正常' },
})
</script>

<style scoped>
.badge { display: inline-block; padding: 8rpx 16rpx; border-radius: 999rpx; font-size: 22rpx; }
.badge-normal { background: #e7f5eb; color: #2f7d4a; }
.badge-expiring { background: #fff2cf; color: #9a6500; }
.badge-today { background: #ffe1c5; color: #b44b00; }
.badge-expired { background: #fde1e1; color: #b52f37; }
</style>

