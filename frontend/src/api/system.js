import request from './request'

export function fetchHealth() {
  return request.get('/health', { silent: true })
}