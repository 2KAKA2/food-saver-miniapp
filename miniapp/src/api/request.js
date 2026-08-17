import { clearHouseholdCaches } from '../utils/householdCache'
import {
  API_BASE_URL,
  API_PREFIX,
  API_TRANSPORT,
  CLOUDBASE_ENV_ID,
  CLOUDBASE_SERVICE,
  validateCloudBaseConfig,
} from '../config/runtime'

const BASE_URL = API_BASE_URL
const TOKEN_KEY = 'food_saver_access_token'
const HOUSEHOLD_KEY = 'food_saver_household_id'

function authHeaders() {
  const token = uni.getStorageSync(TOKEN_KEY)
  const householdId = uni.getStorageSync(HOUSEHOLD_KEY)
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(householdId ? { 'X-Household-Id': String(householdId) } : {}),
  }
}

function handleUnauthorized(path, statusCode) {
  if (statusCode !== 401 || path.startsWith('/auth/')) return
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(HOUSEHOLD_KEY)
  clearHouseholdCaches()
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]?.route || ''
  if (current !== 'pages/login/index') {
    uni.reLaunch({ url: '/pages/login/index' })
  }
}

function errorMessage(data, fallback = '请求失败') {
  if (typeof data === 'string') return data
  if (data?.detail && typeof data.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).join('；')
  return fallback
}

export function request(path, options = {}) {
  // #ifdef MP-WEIXIN
  if (API_TRANSPORT === 'cloudbase') return cloudBaseRequest(path, options)
  // #endif
  return httpRequest(path, options)
}

function httpRequest(path, options = {}) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${path}`,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        ...(options.skipAuth ? {} : authHeaders()),
        ...(options.header || {}),
      },
      timeout: options.timeout || 60000,
      success: ({ statusCode, data }) => {
        if (statusCode >= 200 && statusCode < 300) resolve(data)
        else {
          handleUnauthorized(path, statusCode)
          reject(new Error(errorMessage(data, `请求失败（${statusCode}）`)))
        }
      },
      fail: (error) => reject(new Error(error.errMsg || '无法连接后端服务')),
    })
  })
}

// #ifdef MP-WEIXIN
function cloudBaseRequest(path, options = {}) {
  try {
    validateCloudBaseConfig()
  } catch (error) {
    return Promise.reject(error)
  }
  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: { env: CLOUDBASE_ENV_ID },
      path: `${API_PREFIX}${path}`,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'X-WX-SERVICE': CLOUDBASE_SERVICE,
        'Content-Type': 'application/json',
        ...(options.skipAuth ? {} : authHeaders()),
        ...(options.header || {}),
      },
      success: ({ statusCode, data }) => {
        let parsed = data
        if (typeof parsed === 'string') {
          try {
            parsed = JSON.parse(parsed)
          } catch (_) {}
        }
        if (statusCode >= 200 && statusCode < 300) resolve(parsed)
        else {
          handleUnauthorized(path, statusCode)
          reject(new Error(errorMessage(parsed, `请求失败（${statusCode}）`)))
        }
      },
      fail: (error) => reject(new Error(error.errMsg || '无法连接云托管服务')),
    })
  })
}

function readImageAsBase64(filePath) {
  return new Promise((resolve, reject) => {
    wx.getFileSystemManager().readFile({
      filePath,
      encoding: 'base64',
      success: ({ data }) => resolve(data),
      fail: (error) => reject(new Error(error.errMsg || '无法读取所选图片')),
    })
  })
}

function inferImageType(filePath) {
  const normalized = String(filePath).split('?')[0].toLowerCase()
  if (normalized.endsWith('.png')) return 'image/png'
  if (normalized.endsWith('.webp')) return 'image/webp'
  if (normalized.endsWith('.jpg') || normalized.endsWith('.jpeg')) return 'image/jpeg'
  return null
}

async function uploadCloudBaseImage(filePath) {
  const imageBase64 = await readImageAsBase64(filePath)
  return cloudBaseRequest('/ai/recognize-ingredients/base64', {
    method: 'POST',
    data: {
      image_base64: imageBase64,
      content_type: inferImageType(filePath),
    },
  })
}
// #endif

export function uploadIngredientImage(filePath) {
  // #ifdef MP-WEIXIN
  if (API_TRANSPORT === 'cloudbase') return uploadCloudBaseImage(filePath)
  // #endif
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${BASE_URL}/ai/recognize-ingredients`,
      filePath,
      name: 'file',
      header: authHeaders(),
      timeout: 60000,
      success: ({ statusCode, data }) => {
        let parsed = data
        try {
          parsed = JSON.parse(data)
        } catch (_) {}
        if (statusCode >= 200 && statusCode < 300) resolve(parsed)
        else {
          handleUnauthorized('/ai/recognize-ingredients', statusCode)
          reject(new Error(errorMessage(parsed, `识别失败（${statusCode}）`)))
        }
      },
      fail: (error) => reject(new Error(error.errMsg || '图片上传失败')),
    })
  })
}

export { BASE_URL }
