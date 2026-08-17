import { request, uploadIngredientImage } from './request'

export const api = {
  wechatLogin: (data) => request('/auth/wechat', { method: 'POST', data, skipAuth: true }),
  devLogin: (data) => request('/auth/dev', { method: 'POST', data, skipAuth: true }),
  me: () => request('/auth/me'),
  updateProfile: (data) => request('/auth/profile', { method: 'PUT', data }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  households: () => request('/households'),
  currentHousehold: () => request('/households/current'),
  createHousehold: (data) => request('/households', { method: 'POST', data }),
  updateHousehold: (data) => request('/households/current', { method: 'PUT', data }),
  createInvite: (data = {}) => request('/households/current/invites', { method: 'POST', data }),
  joinHousehold: (data) => request('/households/join', { method: 'POST', data }),
  removeMember: (userId) => request(`/households/current/members/${userId}`, { method: 'DELETE' }),
  transferOwner: (userId) => request('/households/current/transfer', { method: 'POST', data: { new_owner_user_id: userId } }),
  leaveHousehold: () => request('/households/current/leave', { method: 'POST' }),
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
