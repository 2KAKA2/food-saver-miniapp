import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api'
import { LEGAL_VERSION } from '../config/legal'
import { clearHouseholdCaches } from '../utils/householdCache'

export const TOKEN_KEY = 'food_saver_access_token'
export const HOUSEHOLD_KEY = 'food_saver_household_id'
export const AUTH_MODE = import.meta.env.VITE_AUTH_MODE || 'wechat'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(uni.getStorageSync(TOKEN_KEY) || '')
  const user = ref(null)
  const households = ref([])
  const currentHouseholdId = ref(Number(uni.getStorageSync(HOUSEHOLD_KEY)) || null)
  const authenticated = computed(() => Boolean(token.value && user.value))
  const currentHousehold = computed(() =>
    households.value.find((item) => item.id === currentHouseholdId.value) || null
  )

  function chooseCurrentHousehold() {
    const exists = households.value.some((item) => item.id === currentHouseholdId.value)
    if (!exists) currentHouseholdId.value = households.value[0]?.id || null
    if (currentHouseholdId.value) uni.setStorageSync(HOUSEHOLD_KEY, currentHouseholdId.value)
    else uni.removeStorageSync(HOUSEHOLD_KEY)
  }

  function applyLogin(data) {
    token.value = data.access_token
    user.value = data.user
    households.value = data.households || []
    uni.setStorageSync(TOKEN_KEY, token.value)
    chooseCurrentHousehold()
  }

  async function refresh() {
    if (!token.value) return false
    try {
      const data = await api.me()
      user.value = data.user
      households.value = data.households || []
      chooseCurrentHousehold()
      return true
    } catch (_) {
      clearSession()
      return false
    }
  }

  function wxLoginCode() {
    return new Promise((resolve, reject) => {
      uni.login({
        provider: 'weixin',
        success: ({ code }) => (code ? resolve(code) : reject(new Error('微信未返回登录凭证'))),
        fail: () => reject(new Error('微信登录失败，请稍后重试')),
      })
    })
  }

  async function login() {
    let data
    if (AUTH_MODE === 'dev') {
      data = await api.devLogin({
        openid: import.meta.env.VITE_DEV_OPENID || 'local-user',
        nickname: '本地体验用户',
        dev_key: import.meta.env.VITE_DEV_LOGIN_KEY || '',
        legal_version: LEGAL_VERSION,
      })
    } else {
      const code = await wxLoginCode()
      data = await api.wechatLogin({ code, legal_version: LEGAL_VERSION })
    }
    applyLogin(data)
    return data
  }

  function switchHousehold(id) {
    const target = households.value.find((item) => item.id === Number(id))
    if (!target) return false
    currentHouseholdId.value = target.id
    uni.setStorageSync(HOUSEHOLD_KEY, target.id)
    return true
  }

  function clearSession() {
    token.value = ''
    user.value = null
    households.value = []
    currentHouseholdId.value = null
    uni.removeStorageSync(TOKEN_KEY)
    uni.removeStorageSync(HOUSEHOLD_KEY)
    clearHouseholdCaches()
  }

  async function logout() {
    try {
      if (token.value) await api.logout()
    } finally {
      clearSession()
    }
  }

  return {
    token,
    user,
    households,
    currentHouseholdId,
    currentHousehold,
    authenticated,
    login,
    refresh,
    switchHousehold,
    clearSession,
    logout,
  }
})
