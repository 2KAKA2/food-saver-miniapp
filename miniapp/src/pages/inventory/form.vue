<template>
  <view class="page">
    <view class="photo-card card">
      <view>
        <text class="photo-title">拍照识别食材</text>
        <text class="photo-desc">AI 只提供候选，保存前可继续修改</text>
      </view>
      <button class="camera-button" :loading="recognizing" @tap="chooseImage">拍照识别</button>
    </view>

    <view v-if="recognized.length" class="recognized card">
      <text class="block-title">请选择识别结果</text>
      <view v-for="item in recognized" :key="item.name" class="recognized-row" @tap="adopt(item)">
        <text>{{ item.name }} · 约 {{ item.quantity }} {{ item.unit }}</text>
        <text class="adopt">填入 ›</text>
      </view>
    </view>

    <view class="card form-card">
      <text class="block-title">{{ editId ? '编辑库存批次' : '手动录入' }}</text>
      <view class="quick-list">
        <text v-for="item in quickFoods" :key="item.name" class="quick" @tap="adopt(item)">{{ item.name }}</text>
      </view>

      <view class="field">
        <text class="label">食材名称 *</text>
        <input v-model="form.name" class="input" placeholder="例如：西红柿" />
      </view>
      <view class="field">
        <text class="label">分类</text>
        <picker :range="categories" :value="categoryIndex" @change="form.category = categories[$event.detail.value]">
          <view class="input picker">{{ form.category }}</view>
        </picker>
      </view>
      <view class="two-columns">
        <view class="field">
          <text class="label">数量 *</text>
          <input v-model="form.quantity" class="input" type="digit" placeholder="1" />
        </view>
        <view class="field">
          <text class="label">单位 *</text>
          <picker :range="units" :value="unitIndex" @change="form.unit = units[$event.detail.value]">
            <view class="input picker">{{ form.unit }}</view>
          </picker>
        </view>
      </view>
      <view class="field">
        <text class="label">存放位置</text>
        <picker :range="locations" :value="locationIndex" @change="form.location = locations[$event.detail.value]">
          <view class="input picker">{{ form.location }}</view>
        </picker>
      </view>
      <view class="field">
        <text class="label">购买日期</text>
        <picker mode="date" :value="form.purchase_date" @change="form.purchase_date = $event.detail.value">
          <view class="input picker">{{ form.purchase_date || '请选择' }}</view>
        </picker>
      </view>
      <view class="field">
        <text class="label">到期日期</text>
        <picker mode="date" :value="form.expiry_date" :start="form.purchase_date" @change="form.expiry_date = $event.detail.value">
          <view class="input picker">{{ form.expiry_date || '请选择' }}</view>
        </picker>
      </view>
      <view class="field">
        <text class="label">备注</text>
        <textarea v-model="form.note" class="textarea" maxlength="255" placeholder="可选" />
      </view>
    </view>

    <button class="primary-button save" :loading="saving" @tap="save">{{ editId ? '保存修改' : '加入库存' }}</button>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../api'

const editId = ref(null)
const saving = ref(false)
const recognizing = ref(false)
const recognized = ref([])
const categories = ['蔬菜', '水果', '蛋奶', '肉类', '主食', '调料', '其他']
const units = ['个', '盒', '袋', '瓶', 'g', 'kg', 'ml', '份']
const locations = ['冷藏', '冷冻', '橱柜', '其他']
const quickFoods = [
  { name: '西红柿', category: '蔬菜', quantity: 2, unit: '个' },
  { name: '鸡蛋', category: '蛋奶', quantity: 6, unit: '个' },
  { name: '牛奶', category: '蛋奶', quantity: 1, unit: '盒' },
  { name: '土豆', category: '蔬菜', quantity: 3, unit: '个' },
]
const form = reactive({ name: '', category: '蔬菜', quantity: '1', unit: '个', location: '冷藏', purchase_date: '', expiry_date: '', note: '' })
const categoryIndex = computed(() => Math.max(0, categories.indexOf(form.category)))
const unitIndex = computed(() => Math.max(0, units.indexOf(form.unit)))
const locationIndex = computed(() => Math.max(0, locations.indexOf(form.location)))

function adopt(item) {
  form.name = item.name
  form.category = item.category || '其他'
  form.quantity = String(item.quantity || 1)
  form.unit = item.unit || '份'
}

function chooseImage() {
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    sourceType: ['camera', 'album'],
    success: async ({ tempFilePaths }) => {
      recognizing.value = true
      try {
        const result = await api.recognizeIngredients(tempFilePaths[0])
        recognized.value = result.items || []
        uni.showToast({ title: result.source === 'ai' ? '识别完成' : '已使用演示识别', icon: 'none' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none' })
      } finally {
        recognizing.value = false
      }
    },
  })
}

async function save() {
  if (!form.name.trim() || Number(form.quantity) <= 0) {
    uni.showToast({ title: '请填写正确的名称和数量', icon: 'none' })
    return
  }
  saving.value = true
  try {
    const payload = {
      ...form,
      name: form.name.trim(),
      quantity: String(form.quantity),
      purchase_date: form.purchase_date || null,
      expiry_date: form.expiry_date || null,
    }
    if (editId.value) await api.updateInventory(editId.value, payload)
    else await api.createInventory(payload)
    uni.showToast({ title: editId.value ? '修改成功' : '已加入库存' })
    setTimeout(() => uni.navigateBack(), 500)
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  } finally {
    saving.value = false
  }
}

onLoad(async (options) => {
  if (!options.id) return
  editId.value = Number(options.id)
  try {
    const items = await api.inventory()
    const item = items.find((entry) => entry.id === editId.value)
    if (!item) throw new Error('库存记录不存在')
    Object.assign(form, {
      name: item.name,
      category: item.category,
      quantity: String(item.quantity),
      unit: item.unit,
      location: item.location,
      purchase_date: item.purchase_date || '',
      expiry_date: item.expiry_date || '',
      note: item.note || '',
    })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  }
})
</script>

<style scoped>
.photo-card { display: flex; align-items: center; justify-content: space-between; background: #e8f3eb; }
.photo-title, .photo-desc, .block-title { display: block; }
.photo-title { font-size: 30rpx; font-weight: 700; color: #285e3a; }
.photo-desc { margin-top: 8rpx; font-size: 22rpx; color: #64816c; }
.camera-button { margin: 0; padding: 0 24rpx; height: 68rpx; line-height: 68rpx; border-radius: 34rpx; background: #2f7d4a; color: #fff; font-size: 24rpx; }
.recognized { margin-top: 20rpx; }
.recognized-row { display: flex; justify-content: space-between; padding: 22rpx 0; border-bottom: 1rpx solid #edf0ed; font-size: 26rpx; }
.recognized-row:last-child { border-bottom: none; }
.adopt { color: #2f7d4a; }
.form-card { margin-top: 20rpx; }
.block-title { margin-bottom: 24rpx; font-size: 32rpx; font-weight: 700; }
.quick-list { display: flex; flex-wrap: wrap; gap: 14rpx; margin-bottom: 28rpx; }
.quick { padding: 12rpx 22rpx; border-radius: 999rpx; background: #f0f5f1; color: #41634b; font-size: 23rpx; }
.field { flex: 1; margin-top: 24rpx; }
.label { display: block; margin-bottom: 12rpx; color: #647068; font-size: 24rpx; }
.input, .textarea { width: 100%; border: 1rpx solid #dfe5e0; border-radius: 16rpx; background: #fafcfa; font-size: 28rpx; }
.input { height: 76rpx; padding: 0 22rpx; }
.picker { line-height: 76rpx; }
.textarea { height: 140rpx; padding: 20rpx 22rpx; }
.two-columns { display: flex; gap: 20rpx; }
.save { margin-top: 30rpx; }
</style>

