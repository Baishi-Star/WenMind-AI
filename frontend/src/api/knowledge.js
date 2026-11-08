import request from './request'

export function fetchKnowledgeDocuments() {
  return request.get('/knowledge/documents')
}

export function uploadKnowledgeDocument({ file, title, source }) {
  const formData = new FormData()
  formData.append('file', file)
  if (title) formData.append('title', title)
  if (source) formData.append('source', source)
  return request.post('/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function deleteKnowledgeDocument(documentId) {
  return request.delete(`/knowledge/documents/${documentId}`)
}

export function searchKnowledge(payload) {
  return request.post('/knowledge/search', payload, { silent: true, timeout: 30000 })
}

export function fetchKnowledgeStatus() {
  return request.get('/knowledge/status', { silent: true })
}