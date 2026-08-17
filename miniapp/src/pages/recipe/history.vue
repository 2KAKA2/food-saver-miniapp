<template>
  <view class="page">
    <view class="summary card">
      <text class="summary-number">{{ recipes.length }}</text>
      <view>
        <text class="summary-title">份菜谱记录</text>
        <text class="summary-desc">每一次消耗都让食材更有价值</text>
      </view>
    </view>
    <view v-if="loading" class="empty">正在加载...</view>
    <view v-else-if="!recipes.length" class="card empty">还没有菜谱，去生成第一道吧</view>
    <view v-else class="recipe-list">
      <view v-for="recipe in recipes" :key="recipe.id" class="recipe-card card" @tap="openDetail(recipe.id)">
        <view class="recipe-top">
          <text class="recipe-title">{{ recipe.title }}</text>
          <text class="status" :class="recipe.status">{{ recipe.status === 'cooked' ? '已制作' : '待制作' }}</text>
        </view>
        <text class="recipe-meta">{{ recipe.servings }} 人份 · {{ recipe.cook_time_minutes }} 分钟 · {{ recipe.difficulty }}</text>
        <view class="recipe-bottom">
          <text class="source">{{ recipe.source === 'ai' ? 'AI 生成' : '演示菜谱' }}</text>
          <text class="date">{{ formatDate(recipe.created_at) }} ›</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { api } from '../../api'

const recipes = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    recipes.value = await api.recipes()
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  } finally {
    loading.value = false
  }
}

const openDetail = (id) => uni.navigateTo({ url: `/pages/recipe/detail?id=${id}` })
const formatDate = (value) => value ? value.replace('T', ' ').slice(0, 16) : ''

onShow(load)
</script>

<style scoped>
.summary { display: flex; align-items: center; gap: 18rpx; background: #e7f5eb; color: #2c6840; }
.summary-number { font-size: 60rpx; font-weight: 800; }
.summary-title, .summary-desc { display: block; }
.summary-title { font-size: 28rpx; font-weight: 700; }
.summary-desc { margin-top: 6rpx; color: #718c79; font-size: 22rpx; }
.recipe-list { display: flex; flex-direction: column; gap: 20rpx; margin-top: 24rpx; }
.recipe-top, .recipe-bottom { display: flex; justify-content: space-between; align-items: center; gap: 16rpx; }
.recipe-title { flex: 1; font-size: 31rpx; font-weight: 700; }
.status { padding: 8rpx 16rpx; border-radius: 999rpx; background: #fff1cc; color: #956100; font-size: 21rpx; }
.status.cooked { background: #e7f5eb; color: #2f7d4a; }
.recipe-meta { display: block; margin-top: 18rpx; color: #748078; font-size: 24rpx; }
.recipe-bottom { margin-top: 24rpx; padding-top: 18rpx; border-top: 1rpx solid #edf0ed; font-size: 22rpx; }
.source { color: #2f7d4a; }
.date { color: #929b95; }
</style>

