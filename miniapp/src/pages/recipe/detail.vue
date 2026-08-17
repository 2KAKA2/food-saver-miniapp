<template>
  <view class="page">
    <view v-if="loading" class="empty">正在加载...</view>
    <template v-else-if="recipe">
      <view class="hero card">
        <view class="hero-top">
          <text class="dish-icon">🍳</text>
          <text class="source" :class="recipe.source">{{ recipe.source === 'ai' ? 'AI 在线生成' : '演示降级结果' }}</text>
        </view>
        <text class="title">{{ recipe.title }}</text>
        <view class="meta-row">
          <text>{{ recipe.servings }} 人份</text>
          <text>{{ recipe.cook_time_minutes }} 分钟</text>
          <text>{{ recipe.difficulty }}</text>
        </view>
      </view>

      <view class="card section">
        <text class="section-title">现有食材与实际用量</text>
        <view v-for="item in recipe.ingredients" :key="`${item.inventory_id}-${item.name}`" class="ingredient-row">
          <view>
            <text class="ingredient-name">{{ item.name }}</text>
            <text class="ingredient-state">{{ item.available ? '库存已有' : '需要补充' }}</text>
          </view>
          <view v-if="item.inventory_id" class="amount-edit">
            <input v-model="consumptions[item.inventory_id]" class="amount-input" type="digit" :disabled="recipe.status === 'cooked'" />
            <text>{{ item.unit }}</text>
          </view>
          <text v-else>{{ item.quantity }} {{ item.unit }}</text>
        </view>
      </view>

      <view v-if="recipe.missing_ingredients.length" class="card section missing-card">
        <text class="section-title">需要补充</text>
        <text v-for="item in recipe.missing_ingredients" :key="item.name" class="missing-item">{{ item.name }} {{ item.quantity }} {{ item.unit }}</text>
      </view>

      <view class="card section">
        <text class="section-title">制作步骤</text>
        <view v-for="(step, index) in recipe.steps" :key="index" class="step-row">
          <text class="step-number">{{ index + 1 }}</text>
          <text class="step-text">{{ step }}</text>
        </view>
      </view>

      <button v-if="recipe.status !== 'cooked'" class="primary-button cook-button" :loading="cooking" @tap="cook">确认制作并扣减库存</button>
      <view v-else class="cooked-tip">✓ 已完成制作，库存已更新</view>
    </template>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../api'

const recipeId = ref(null)
const recipe = ref(null)
const loading = ref(false)
const cooking = ref(false)
const consumptions = reactive({})

async function load() {
  loading.value = true
  try {
    recipe.value = await api.recipe(recipeId.value)
    recipe.value.ingredients.forEach((item) => {
      if (item.inventory_id) consumptions[item.inventory_id] = String(item.quantity)
    })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  } finally {
    loading.value = false
  }
}

function cookIdempotencyKey() {
  const storageKey = `food_saver_cook_key_${recipeId.value}`
  let value = uni.getStorageSync(storageKey)
  if (!value) {
    value = `${Date.now()}-${Math.random().toString(36).slice(2)}-${recipeId.value}`
    uni.setStorageSync(storageKey, value)
  }
  return { storageKey, value }
}

function cook() {
  const items = Object.entries(consumptions)
    .filter(([, quantity]) => Number(quantity) > 0)
    .map(([inventoryId, quantity]) => ({ inventory_id: Number(inventoryId), quantity: String(quantity) }))
  if (!items.length) {
    uni.showToast({ title: '请填写实际食材用量', icon: 'none' })
    return
  }
  uni.showModal({
    title: '确认制作',
    content: '确认后将按照当前用量扣减库存，是否继续？',
    success: async ({ confirm }) => {
      if (!confirm) return
      cooking.value = true
      try {
        const idempotency = cookIdempotencyKey()
        const result = await api.cookRecipe(recipeId.value, { consumptions: items }, idempotency.value)
        recipe.value = result.recipe
        uni.removeStorageSync(idempotency.storageKey)
        uni.showToast({ title: '库存已更新' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 2500 })
      } finally {
        cooking.value = false
      }
    },
  })
}

onLoad((options) => {
  recipeId.value = Number(options.id)
  load()
})
</script>

<style scoped>
.hero { background: linear-gradient(145deg, #2f7d4a, #438f59); color: #fff; }
.hero-top { display: flex; justify-content: space-between; align-items: center; }
.dish-icon { font-size: 54rpx; }
.source { padding: 8rpx 16rpx; border-radius: 999rpx; background: rgba(255,255,255,.18); font-size: 21rpx; }
.title { display: block; margin-top: 26rpx; font-size: 42rpx; font-weight: 800; }
.meta-row { display: flex; gap: 34rpx; margin-top: 22rpx; color: rgba(255,255,255,.82); font-size: 24rpx; }
.section { margin-top: 22rpx; }
.section-title { display: block; margin-bottom: 16rpx; font-size: 30rpx; font-weight: 700; }
.ingredient-row { display: flex; align-items: center; justify-content: space-between; padding: 20rpx 0; border-bottom: 1rpx solid #edf0ed; font-size: 25rpx; }
.ingredient-row:last-child { border-bottom: none; }
.ingredient-name, .ingredient-state { display: block; }
.ingredient-name { font-size: 27rpx; font-weight: 600; }
.ingredient-state { margin-top: 5rpx; color: #879188; font-size: 21rpx; }
.amount-edit { display: flex; align-items: center; gap: 10rpx; }
.amount-input { width: 100rpx; height: 60rpx; text-align: center; border-radius: 12rpx; background: #f1f5f2; }
.missing-card { background: #fff8e9; }
.missing-item { display: inline-block; margin: 8rpx 12rpx 0 0; padding: 12rpx 18rpx; border-radius: 999rpx; background: #fff0c7; color: #886000; font-size: 23rpx; }
.step-row { display: flex; gap: 18rpx; padding: 20rpx 0; }
.step-number { flex: none; display: grid; place-items: center; width: 48rpx; height: 48rpx; border-radius: 50%; background: #e7f5eb; color: #2f7d4a; font-weight: 700; }
.step-text { flex: 1; line-height: 1.65; font-size: 26rpx; }
.cook-button { margin-top: 28rpx; }
.cooked-tip { margin-top: 28rpx; padding: 26rpx; border-radius: 20rpx; background: #e7f5eb; color: #2f7d4a; text-align: center; font-weight: 600; }
</style>
