import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const apiDir = fileURLToPath(new URL('../src/api', import.meta.url))
const baseUrl = process.env.API_BASE_URL || 'http://127.0.0.1:8000'
const spec = await fetch(`${baseUrl}/openapi.json`).then((response) => {
  if (!response.ok) throw new Error(`OpenAPI 获取失败：HTTP ${response.status}`)
  return response.json()
})

const normalize = (path) => path.replace(/\$\{[^}]+\}/g, '{param}').replace(/\{[^}]+\}/g, '{param}')
const available = new Set()
for (const [path, operations] of Object.entries(spec.paths)) {
  for (const method of Object.keys(operations)) {
    if (['get', 'post', 'put', 'delete', 'patch'].includes(method)) {
      available.add(`${method.toUpperCase()} ${normalize(path)}`)
    }
  }
}

const calls = []
for (const file of readdirSync(apiDir).filter((name) => name.endsWith('.js') && name !== 'request.js')) {
  const source = readFileSync(join(apiDir, file), 'utf8')
  const pattern = /request\.(get|post|put|delete|patch)\(\s*([`'"])([^`'"]+)\2/g
  for (const match of source.matchAll(pattern)) {
    calls.push({ file, method: match[1].toUpperCase(), path: normalize(match[3]) })
  }
}

const missing = calls.filter((call) => !available.has(`${call.method} /api/v1${call.path}`))
console.log(`API 调用：${calls.length}，OpenAPI 操作：${available.size}，未匹配：${missing.length}`)
for (const call of missing) console.log(`MISSING ${call.file} ${call.method} ${call.path}`)
if (missing.length > 0) process.exitCode = 1