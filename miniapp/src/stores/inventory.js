import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'

export const useInventoryStore = defineStore('inventory', () => {
  const items = ref([])
  const loading = ref(false)

  async function load(params = {}) {
    loading.value = true
    try {
      items.value = await api.inventory(params)
      return items.value
    } finally {
      loading.value = false
    }
  }

  return { items, loading, load }
})

