import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'
import { readHouseholdCache, writeHouseholdCache } from '../utils/householdCache'

export const useInventoryStore = defineStore('inventory', () => {
  const items = ref([])
  const loading = ref(false)
  const usingCache = ref(false)
  const cachedAt = ref('')

  function filterCachedItems(cachedItems, params) {
    const keyword = String(params.keyword || '').trim().toLocaleLowerCase()
    return cachedItems.filter((item) => {
      const matchesStatus = !params.status || item.status === params.status
      const matchesKeyword = !keyword || String(item.name || '').toLocaleLowerCase().includes(keyword)
      return matchesStatus && matchesKeyword
    })
  }

  async function load(params = {}) {
    loading.value = true
    usingCache.value = false
    cachedAt.value = ''
    try {
      const result = await api.inventory(params)
      items.value = result
      if (!params.status && !String(params.keyword || '').trim()) {
        writeHouseholdCache('inventory', result)
      }
      return items.value
    } catch (error) {
      const cached = readHouseholdCache('inventory')
      if (!cached || !Array.isArray(cached.data)) {
        items.value = []
        throw error
      }
      items.value = filterCachedItems(cached.data, params)
      usingCache.value = true
      cachedAt.value = cached.savedAt
      return items.value
    } finally {
      loading.value = false
    }
  }

  return { items, loading, usingCache, cachedAt, load }
})
