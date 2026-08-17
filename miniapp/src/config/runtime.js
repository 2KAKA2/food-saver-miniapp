export const API_TRANSPORT = import.meta.env.VITE_API_TRANSPORT || 'http'
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
export const CLOUDBASE_ENV_ID = import.meta.env.VITE_CLOUDBASE_ENV_ID || ''
export const CLOUDBASE_SERVICE = import.meta.env.VITE_CLOUDBASE_SERVICE || ''
export const API_PREFIX = '/api/v1'

export function validateCloudBaseConfig() {
  if (API_TRANSPORT !== 'cloudbase') return
  if (!CLOUDBASE_ENV_ID || !CLOUDBASE_SERVICE) {
    throw new Error('CloudBase 环境 ID 或云托管服务名称尚未配置')
  }
}
