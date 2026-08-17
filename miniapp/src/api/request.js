const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'

function errorMessage(data, fallback = '请求失败') {
  if (typeof data === 'string') return data
  if (data?.detail && typeof data.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).join('；')
  return fallback
}

export function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${path}`,
      method: options.method || 'GET',
      data: options.data,
      header: { 'Content-Type': 'application/json', ...(options.header || {}) },
      timeout: options.timeout || 60000,
      success: ({ statusCode, data }) => {
        if (statusCode >= 200 && statusCode < 300) resolve(data)
        else reject(new Error(errorMessage(data, `请求失败（${statusCode}）`)))
      },
      fail: (error) => reject(new Error(error.errMsg || '无法连接后端服务')),
    })
  })
}

export function uploadIngredientImage(filePath) {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${BASE_URL}/ai/recognize-ingredients`,
      filePath,
      name: 'file',
      timeout: 60000,
      success: ({ statusCode, data }) => {
        let parsed = data
        try {
          parsed = JSON.parse(data)
        } catch (_) {}
        if (statusCode >= 200 && statusCode < 300) resolve(parsed)
        else reject(new Error(errorMessage(parsed, `识别失败（${statusCode}）`)))
      },
      fail: (error) => reject(new Error(error.errMsg || '图片上传失败')),
    })
  })
}

export { BASE_URL }

