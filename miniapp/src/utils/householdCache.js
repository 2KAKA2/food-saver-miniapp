const CACHE_PREFIX = 'food_saver_household_cache_'
const HOUSEHOLD_KEY = 'food_saver_household_id'

function cacheKey(scope) {
  const householdId = Number(uni.getStorageSync(HOUSEHOLD_KEY))
  if (!householdId) return ''
  return `${CACHE_PREFIX}${householdId}_${scope}`
}

export function writeHouseholdCache(scope, data) {
  const key = cacheKey(scope)
  if (!key) return
  uni.setStorageSync(key, {
    savedAt: new Date().toISOString(),
    data,
  })
}

export function readHouseholdCache(scope) {
  const key = cacheKey(scope)
  if (!key) return null
  const cached = uni.getStorageSync(key)
  if (!cached || typeof cached !== 'object' || !cached.savedAt || cached.data === undefined) {
    return null
  }
  return cached
}

export function clearHouseholdCaches() {
  let keys = []
  try {
    keys = uni.getStorageInfoSync()?.keys || []
  } catch (_) {
    return
  }
  keys
    .filter((key) => key.startsWith(CACHE_PREFIX))
    .forEach((key) => uni.removeStorageSync(key))
}
