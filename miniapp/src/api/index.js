import { request, uploadIngredientImage } from './request'

export const api = {
  dashboard: () => request('/dashboard'),
  inventory: (params = {}) => {
    const query = Object.entries(params)
      .filter(([, value]) => value !== '' && value != null)
      .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
      .join('&')
    return request(`/inventory${query ? `?${query}` : ''}`)
  },
  createInventory: (data) => request('/inventory', { method: 'POST', data }),
  updateInventory: (id, data) => request(`/inventory/${id}`, { method: 'PUT', data }),
  deleteInventory: (id) => request(`/inventory/${id}`, { method: 'DELETE' }),
  recognizeIngredients: uploadIngredientImage,
  generateRecipe: (data) => request('/recipes/generate', { method: 'POST', data, timeout: 90000 }),
  recipes: () => request('/recipes'),
  recipe: (id) => request(`/recipes/${id}`),
  cookRecipe: (id, data) => request(`/recipes/${id}/cook`, { method: 'POST', data }),
}

