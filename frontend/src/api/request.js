import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

request.interceptors.request.use(
  (config) => {
    // 后续登录阶段在此统一注入访问令牌
    const token = localStorage.getItem('wenmind_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

request.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) {
        const error = new Error(body.message || '请求失败')
        error.code = body.code
        error.requestId = body.request_id
        return Promise.reject(error)
      }
      return body
    }
    return body
  },
  (error) => {
    const body = error.response?.data
    const message =
      body?.message ||
      (error.code === 'ECONNABORTED'
        ? '请求超时，请稍后重试'
        : '无法连接后端服务，请确认后端已启动')
    const normalized = new Error(message)
    normalized.code = body?.code ?? error.response?.status ?? -1
    normalized.requestId = body?.request_id
    normalized.status = error.response?.status
    if (!error.config?.silent) {
      ElMessage.error(message)
    }
    return Promise.reject(normalized)
  },
)

export default request