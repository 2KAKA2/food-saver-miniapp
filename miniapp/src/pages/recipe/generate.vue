<template>
  <view class="page">
    <view class="intro card">
      <text class="intro-icon">✨</text>
      <view>
        <text class="intro-title">让库存变成今晚的菜</text>
        <text class="intro-desc">系统会优先选择临期食材，减少浪费</text>
      </view>
    </view>

    <view class="card section">
      <view class="section-head">
        <text class="section-title">选择食材</text>
        <text class="select-all" @tap="toggleAll">{{ allSelected ? '取消全选' : '全选' }}</text>
      </view>
      <view v-if="loading" class="empty">正在加载...</view>
      <ErrorState v-else-if="loadError" :message="loadError" @retry="loadInventory" />
      <view v-else-if="!inventory.length" class="empty">请先录入库存食材</view>
      <checkbox-group v-else @change="selectedIds = $event.detail.value.map(Number)">
        <label v-for="item in inventory" :key="item.id" class="food-option">
          <checkbox :value="String(item.id)" :checked="selectedIds.includes(item.id)" color="#2f7d4a" />
          <view class="food-info">
            <view class="name-row">
              <text>{{ item.name }}</text>
              <StatusBadge v-if="item.status !== 'normal'" :status="item.status" :text="item.status_text" />
            </view>
            <text class="food-meta">{{ item.quantity }} {{ item.unit }} · {{ item.location }}</text>
          </view>
        </label>
      </checkbox-group>
    </view>

    <view class="card section preferences">
      <text class="section-title">烹饪偏好</text>
      <view class="form-row">
        <text>用餐人数</text>
        <picker :range="servingOptions" :value="servings - 1" @change="servings = Number($event.detail.value) + 1">
          <text class="picker-value">{{ servings }} 人 ›</text>
        </picker>
      </view>
      <view class="form-row">
        <text>口味</text>
        <picker :range="flavors" :value="flavorIndex" @change="flavor = flavors[$event.detail.value]">
          <text class="picker-value">{{ flavor }} ›</text>
        </picker>
      </view>
      <view class="form-row">
        <text>最长时间</text>
        <picker :range="timeLabels" :value="timeIndex" @change="maxMinutes = timeValues[$event.detail.value]">
          <text class="picker-value">{{ maxMinutes }} 分钟 ›</text>
        </picker>
      </view>
    </view>

    <button class="primary-button generate" :loading="generating" @tap="generate">{{ generating ? 'AI 正在设计菜谱...' : '生成今晚的菜谱' }}</button>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { api } from '../../api'
import ErrorState from '../../components/ErrorState.vue'
import StatusBadge from '../../components/StatusBadge.vue'

const inventory = ref([])
const selectedIds = ref([])
const loading = ref(false)
const loadError = ref('')
const generating = ref(false)
const servings = ref(2)
const flavor = ref('家常')
const maxMinutes = ref(30)
const servingOptions = Array.from({ length: 10 }, (_, index) => `${index + 1} 人`)
const flavors = ['家常', '清淡', '香辣', '酸甜', '低脂']
const timeValues = [15, 30, 45, 60]
const timeLabels = timeValues.map((value) => `${value} 分钟`)
const flavorIndex = computed(() => flavors.indexOf(flavor.value))
const timeIndex = computed(() => timeValues.indexOf(maxMinutes.value))
const allSelected = computed(() => inventory.value.length > 0 && selectedIds.value.length === inventory.value.length)

async function loadInventory() {
  loading.value = true
  loadError.value = ''
  try {
    inventory.value = (await api.inventory()).filter((item) => item.status !== 'expired')
    selectedIds.value = inventory.value.map((item) => item.id)
  } catch (error) {
    loadError.value = error.message
  } finally {
    loading.value = false
  }
}

function toggleAll() {
  selectedIds.value = allSelected.value ? [] : inventory.value.map((item) => item.id)
}

async function generate() {
  if (!selectedIds.value.length) {
    uni.showToast({ title: '请至少选择一种食材', icon: 'none' })
    return
  }
  generating.value = true
  try {
    const recipe = await api.generateRecipe({
      inventory_ids: selectedIds.value,
      servings: servings.value,
      flavor: flavor.value,
      max_minutes: maxMinutes.value,
    })
    uni.navigateTo({ url: `/pages/recipe/detail?id=${recipe.id}` })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none', duration: 2500 })
  } finally {
    generating.value = false
  }
}

onShow(loadInventory)
</script>

<style scoped>
.intro { display: flex; align-items: center; gap: 22rpx; background: linear-gradient(135deg, #e7f5eb, #f5fbf6); }
.intro-icon { font-size: 56rpx; }
.intro-title, .intro-desc { display: block; }
.intro-title { font-size: 31rpx; font-weight: 700; color: #285e3a; }
.intro-desc { margin-top: 8rpx; color: #718078; font-size: 23rpx; }
.section { margin-top: 22rpx; }
.section-head { display: flex; justify-content: space-between; align-items: center; }
.section-title { font-size: 30rpx; font-weight: 700; }
.select-all { color: #2f7d4a; font-size: 24rpx; }
.food-option { display: flex; align-items: center; gap: 18rpx; padding: 24rpx 0; border-bottom: 1rpx solid #edf0ed; }
.food-option:last-child { border-bottom: none; }
.food-info { flex: 1; }
.name-row { display: flex; justify-content: space-between; align-items: center; font-size: 28rpx; font-weight: 600; }
.food-meta { display: block; margin-top: 8rpx; color: #818c84; font-size: 23rpx; }
.preferences .section-title { display: block; margin-bottom: 8rpx; }
.form-row { display: flex; justify-content: space-between; padding: 25rpx 0; border-bottom: 1rpx solid #edf0ed; font-size: 27rpx; }
.form-row:last-child { border-bottom: none; }
.picker-value { color: #2f7d4a; }
.generate { margin-top: 28rpx; }
</style>
