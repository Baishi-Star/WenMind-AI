import request from './request'

export function login(payload) {
  return request.post('/auth/login', payload, { silent: true })
}

export function fetchCurrentUser() {
  return request.get('/auth/me', { silent: true })
}