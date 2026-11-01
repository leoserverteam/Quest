import axios from 'axios'

const apiBase = (import.meta as any).env?.VITE_API_BASE_URL || '/api'

const api = axios.create({
  baseURL: apiBase,
})

export default api
export const publicBase = (import.meta as any).env?.VITE_PUBLIC_BASE_URL || window.location.origin
