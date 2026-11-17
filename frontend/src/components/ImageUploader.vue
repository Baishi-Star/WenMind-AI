<template>
  <div class="image-uploader">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="支持 JPG / PNG / WEBP 图片"
      :description="`单张不超过 ${maxMb} MB，最多 ${maxPages} 页，总量不超过 ${totalMaxMb} MB。可多选、拖拽排序、旋转。`"
      class="uploader-tip"
    />

    <div class="uploader-actions">
      <el-upload
        :auto-upload="false"
        multiple
        :show-file-list="false"
        accept="image/jpeg,image/png,image/webp"
        :on-change="handleSelect"
      >
        <el-button
          type="primary"
          :loading="uploading"
        >
          选择并上传照片
        </el-button>
      </el-upload>
      <span class="uploader-count">已上传 {{ files.length }} / {{ maxPages }} 页</span>
    </div>

    <div
      v-if="compressionInfo"
      class="compression-info"
    >
      <img
        v-if="compressionInfo.previewUrl"
        :src="compressionInfo.previewUrl"
        alt="原图预览"
        class="compression-preview"
      >
      <div class="compression-meta">
        <strong>{{ compressionInfo.compressed ? '已压缩上传' : '未压缩（原图上传）' }}</strong>
        <span>
          {{ compressionInfo.compressed
            ? `已压缩：${formatSize(compressionInfo.originalSize)} → ${formatSize(compressionInfo.uploadSize)}`
            : `原图体积：${formatSize(compressionInfo.originalSize)}` }}
        </span>
      </div>
    </div>

    <el-alert
      v-if="error"
      type="error"
      :closable="false"
      show-icon
      :title="error"
      class="uploader-error"
    />

    <div
      v-if="files.length"
      class="thumb-list"
    >
      <article
        v-for="(file, index) in files"
        :key="file.id"
        class="thumb"
        :class="{ 'is-first': index === 0 }"
      >
        <div class="thumb__preview">
          <img
            v-if="previews[file.id]"
            :src="previews[file.id]"
            :alt="`第 ${index + 1} 页`"
            :style="{ transform: `rotate(${file.rotation}deg)` }"
          >
          <span
            v-else
            class="thumb__loading"
          >图片加载中…</span>
          <span class="thumb__badge">第 {{ index + 1 }} 页</span>
        </div>
        <div class="thumb__info">
          <span class="thumb__name">{{ file.original_filename }}</span>
          <span class="thumb__meta">{{ formatSize(file.file_size) }} · {{ statusLabel(file.extraction_status) }}</span>
        </div>
        <div class="thumb__ops">
          <el-button
            size="small"
            :disabled="index === 0"
            @click="move(index, -1)"
          >
            上移
          </el-button>
          <el-button
            size="small"
            :disabled="index === files.length - 1"
            @click="move(index, 1)"
          >
            下移
          </el-button>
          <el-button
            size="small"
            @click="rotate(index)"
          >
            旋转
          </el-button>
          <el-button
            size="small"
            type="danger"
            plain
            :loading="deletingId === file.id"
            @click="remove(file)"
          >
            删除
          </el-button>
        </div>
      </article>
    </div>
    <el-empty
      v-else
      description="尚未上传作文照片"
      :image-size="70"
    />
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  deleteSubmissionFile,
  fetchSubmissionFiles,
  loadAuthorizedImage,
  reorderSubmissionFiles,
  uploadSubmissionFiles,
} from '@/api/submission'

const props = defineProps({
  submissionId: { type: Number, required: true },
  maxMb: { type: Number, default: 10 },
  totalMaxMb: { type: Number, default: 50 },
  maxPages: { type: Number, default: 20 },
})
const emit = defineEmits(['changed'])

const files = ref([])
const previews = ref({})
const uploading = ref(false)
const deletingId = ref(null)
const error = ref('')
const objectUrls = new Set()
const compressionInfo = ref(null)
let compressionPreviewUrl = ''
const MAX_EDGE = 1600
const JPEG_QUALITY = 0.82

function revokePreviews() {
  objectUrls.forEach((url) => URL.revokeObjectURL(url))
  objectUrls.clear()
  previews.value = {}
}

async function compressImage(file) {
  if (!window.createImageBitmap || !document.createElement) {
    return { blob: file, originalSize: file.size, compressed: false }
  }
  try {
    const bitmap = await createImageBitmap(file)
    const largest = Math.max(bitmap.width, bitmap.height)
    const scale = largest > MAX_EDGE ? MAX_EDGE / largest : 1
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bitmap.width * scale))
    canvas.height = Math.max(1, Math.round(bitmap.height * scale))
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    if (bitmap.close) bitmap.close()
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY))
    if (!blob || blob.size >= file.size) {
      return { blob: file, originalSize: file.size, compressed: false }
    }
    return {
      blob: new File([blob], `${file.name.replace(/\.[^.]+$/, '')}.jpg`, { type: 'image/jpeg' }),
      originalSize: file.size,
      compressed: true,
    }
  } catch {
    return { blob: file, originalSize: file.size, compressed: false }
  }
}

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function statusLabel(status) {
  return { pending: '待识别', processing: '识别中', done: '识别完成', failed: '识别失败' }[status] || status
}

async function loadFiles() {
  if (!props.submissionId) return
  try {
    const response = await fetchSubmissionFiles(props.submissionId)
    files.value = response.data
    revokePreviews()
    await Promise.all(
      files.value.map(async (file) => {
        try {
          const url = await loadAuthorizedImage(file.id)
          objectUrls.add(url)
          previews.value[file.id] = url
        } catch {
          // 单张图片加载失败不影响列表整体展示
        }
      }),
    )
    emit('changed', files.value.length)
  } catch (requestError) {
    error.value = requestError.message || '图片列表加载失败'
  }
}

async function handleSelect(file) {
  const raw = file.raw
  if (!raw) return
  error.value = ''
  uploading.value = true
  if (compressionPreviewUrl) URL.revokeObjectURL(compressionPreviewUrl)
  compressionPreviewUrl = URL.createObjectURL(raw)
  compressionInfo.value = {
    originalSize: raw.size,
    uploadSize: raw.size,
    compressed: false,
    previewUrl: compressionPreviewUrl,
  }
  try {
    const result = await compressImage(raw)
    compressionInfo.value = {
      originalSize: result.originalSize,
      uploadSize: result.blob.size,
      compressed: result.compressed,
      previewUrl: compressionPreviewUrl,
    }
    await uploadSubmissionFiles(props.submissionId, [result.blob], 'photo')
    ElMessage.success(
      result.compressed
        ? `已压缩上传（${formatSize(result.originalSize)} → ${formatSize(result.blob.size)}）`
        : '已上传原图',
    )
    await loadFiles()
  } catch (requestError) {
    error.value = requestError.message || '图片上传失败'
  } finally {
    uploading.value = false
  }
}

async function persistOrder() {
  const payload = files.value.map((file) => ({ file_id: file.id, rotation: file.rotation }))
  await reorderSubmissionFiles(props.submissionId, payload)
}

async function move(index, delta) {
  const target = index + delta
  if (target < 0 || target >= files.value.length) return
  const list = [...files.value]
  ;[list[index], list[target]] = [list[target], list[index]]
  files.value = list
  try {
    await persistOrder()
    await loadFiles()
  } catch (requestError) {
    error.value = requestError.message || '页序保存失败'
    await loadFiles()
  }
}

async function rotate(index) {
  files.value[index].rotation = (files.value[index].rotation + 90) % 360
  try {
    await persistOrder()
    await loadFiles()
  } catch (requestError) {
    error.value = requestError.message || '旋转保存失败'
    await loadFiles()
  }
}

async function remove(file) {
  try {
    await ElMessageBox.confirm(`删除第 ${file.sort_order} 页图片？`, '确认删除', { type: 'warning' })
  } catch {
    return
  }
  deletingId.value = file.id
  try {
    await deleteSubmissionFile(props.submissionId, file.id)
    ElMessage.success('图片已删除')
    await loadFiles()
  } catch (requestError) {
    error.value = requestError.message || '删除失败'
  } finally {
    deletingId.value = null
  }
}

defineExpose({ loadFiles, fileCount: () => files.value.length })
onBeforeUnmount(() => {
  revokePreviews()
  if (compressionPreviewUrl) URL.revokeObjectURL(compressionPreviewUrl)
})
loadFiles()
</script>

<style scoped>
.uploader-tip { margin-bottom: 14px; }
.uploader-actions { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
.uploader-count { color: var(--wm-text-secondary); font-size: 12px; }
.uploader-error { margin-bottom: 14px; }
.compression-info { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; padding: 10px 12px; border-radius: 10px; background: var(--wm-bg-soft); }
.compression-preview { width: 72px; height: 72px; object-fit: cover; border-radius: 8px; border: 1px solid var(--wm-border); }
.compression-meta { display: flex; flex-direction: column; gap: 4px; }
.compression-meta strong { font-size: 12px; }
.compression-meta span { color: var(--wm-text-secondary); font-size: 11px; }
.thumb-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 14px; }
.thumb { border: 1px solid var(--wm-border); border-radius: 12px; overflow: hidden; background: #fff; }
.thumb.is-first { border-color: var(--wm-primary); }
.thumb__preview { position: relative; height: 190px; display: grid; place-items: center; overflow: hidden; background: #f6f7fb; }
.thumb__preview img { max-height: 100%; max-width: 100%; object-fit: contain; transition: transform 0.2s ease; }
.thumb__loading { color: var(--wm-text-secondary); font-size: 11px; }
.thumb__badge { position: absolute; top: 8px; left: 8px; padding: 2px 8px; border-radius: 999px; background: rgba(24, 33, 61, 0.72); color: #fff; font-size: 10px; }
.thumb__info { padding: 10px 12px 4px; display: flex; flex-direction: column; gap: 3px; }
.thumb__name { font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.thumb__meta { color: var(--wm-text-secondary); font-size: 10px; }
.thumb__ops { padding: 8px 12px 12px; display: flex; flex-wrap: wrap; gap: 6px; }
</style>