<template>
  <div class="essay-viewer">
    <div
      v-if="files.length"
      class="viewer-layout"
    >
      <aside class="viewer-thumbs">
        <button
          v-for="(file, index) in files"
          :key="file.id"
          type="button"
          class="viewer-thumb"
          :class="{ 'is-active': index === activeIndex }"
          @click="activeIndex = index"
        >
          <img
            v-if="previews[file.id]"
            :src="previews[file.id]"
            :alt="`第 ${index + 1} 页`"
          >
          <span class="viewer-thumb__label">第 {{ index + 1 }} 页</span>
        </button>
      </aside>

      <section class="viewer-stage">
        <div class="viewer-toolbar">
          <span v-if="activeFile">第 {{ activeIndex + 1 }} / {{ files.length }} 页 · {{ activeFile.original_filename }}</span>
          <div class="viewer-toolbar__ops">
            <el-button
              size="small"
              :disabled="activeIndex === 0"
              @click="activeIndex -= 1"
            >
              上一页
            </el-button>
            <el-button
              size="small"
              :disabled="activeIndex === files.length - 1"
              @click="activeIndex += 1"
            >
              下一页
            </el-button>
            <el-button
              size="small"
              @click="rotateActive"
            >
              旋转 90°
            </el-button>
            <el-button
              size="small"
              @click="zoom = Math.max(0.5, zoom - 0.2)"
            >
              缩小
            </el-button>
            <el-button
              size="small"
              @click="zoom = Math.min(3, zoom + 0.2)"
            >
              放大
            </el-button>
            <el-button
              size="small"
              @click="zoom = 1"
            >
              复位
            </el-button>
          </div>
        </div>

        <div class="viewer-canvas">
          <div
            v-if="activeFile && previews[activeFile.id]"
            class="viewer-image-wrap"
            :style="{ transform: `scale(${zoom}) rotate(${rotation}deg)` }"
          >
            <img
              :src="previews[activeFile.id]"
              :alt="`作文第 ${activeIndex + 1} 页`"
            >
            <template v-if="showAnnotations">
              <span
                v-for="item in activeAnnotations"
                :key="item.id"
                class="annotation-box"
                :class="`is-${item.source}`"
                :style="annotationStyle(item)"
                :title="item.note || item.label"
              />
            </template>
          </div>
          <el-empty
            v-else
            description="图片加载中或已失效"
            :image-size="70"
          />
        </div>

        <div
          v-if="activeFile"
          class="viewer-meta"
        >
          <div class="viewer-meta__row">
            <el-tag
              size="small"
              :type="activeFile.extraction_status === 'done' ? 'success' : 'warning'"
            >
              {{ statusLabel(activeFile.extraction_status) }}
            </el-tag>
            <span>{{ formatSize(activeFile.file_size) }}</span>
            <span v-if="activeFile.width">· {{ activeFile.width }}×{{ activeFile.height }}</span>
            <el-switch
              v-model="showAnnotations"
              size="small"
              active-text="展示标注"
              :disabled="annotations.length === 0"
            />
            <span class="viewer-hint">{{ annotations.length ? `共 ${annotations.length} 处标注` : '暂无标注' }}</span>
          </div>
          <div
            v-if="activeFile.extracted_text"
            class="viewer-text"
          >
            <strong>AI 识别文本（需人工核对，可能与原文有出入）</strong>
            <pre>{{ activeFile.extracted_text }}</pre>
          </div>
          <el-alert
            v-else
            type="info"
            :closable="false"
            show-icon
            title="该页尚无识别文本"
          />
          <p
            v-if="activeFile.error_message"
            class="viewer-error"
          >
            识别失败原因：{{ activeFile.error_message }}
          </p>
        </div>
      </section>
    </div>
    <el-empty
      v-else
      description="该作文没有上传图片原文（文字作文请在正文区查看）"
      :image-size="70"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { loadAuthorizedImage } from '@/api/submission'

const props = defineProps({
  files: { type: Array, default: () => [] },
  annotations: { type: Array, default: () => [] },
})

const activeIndex = ref(0)
const rotation = ref(0)
const zoom = ref(1)
const previews = ref({})
const showAnnotations = ref(false)
const objectUrls = new Set()

const activeFile = computed(() => props.files[activeIndex.value] || null)

const activeAnnotations = computed(() => {
  const file = activeFile.value
  if (!file) return []
  return props.annotations.filter(
    (item) => item.submission_file_id === file.id || (item.submission_file_id === null && item.page_no === activeIndex.value + 1),
  )
})

function annotationStyle(item) {
  // 坐标为归一化值（0~1），用百分比定位，缩放时不会错位。
  if (item.shape === 'point') {
    return {
      left: `${item.x * 100}%`,
      top: `${item.y * 100}%`,
      width: '14px',
      height: '14px',
      marginLeft: '-7px',
      marginTop: '-7px',
      borderRadius: '50%',
      borderColor: item.color,
      background: `${item.color}55`,
    }
  }
  return {
    left: `${item.x * 100}%`,
    top: `${item.y * 100}%`,
    width: `${item.width * 100}%`,
    height: `${item.height * 100}%`,
    borderColor: item.color,
    background: `${item.color}22`,
  }
}

function statusLabel(status) {
  return { pending: '待识别', processing: '识别中', done: '识别完成', failed: '识别失败' }[status] || status
}

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function revokeAll() {
  objectUrls.forEach((url) => URL.revokeObjectURL(url))
  objectUrls.clear()
  previews.value = {}
}

async function loadPreviews() {
  revokeAll()
  await Promise.all(
    props.files.map(async (file) => {
      try {
        const url = await loadAuthorizedImage(file.id)
        objectUrls.add(url)
        previews.value[file.id] = url
      } catch {
        // 单页失败不影响其他页
      }
    }),
  )
}

function rotateActive() {
  rotation.value = (rotation.value + 90) % 360
}

watch(
  () => props.files,
  (value) => {
    activeIndex.value = 0
    rotation.value = 0
    zoom.value = 1
    if (value.length) loadPreviews()
    else revokeAll()
  },
  { immediate: true, deep: true },
)

watch(activeIndex, () => {
  rotation.value = 0
  zoom.value = 1
})

onBeforeUnmount(revokeAll)
</script>

<style scoped>
.viewer-layout { display: grid; grid-template-columns: 108px minmax(0, 1fr); gap: 14px; }
.viewer-thumbs { display: flex; flex-direction: column; gap: 8px; max-height: 620px; overflow-y: auto; }
.viewer-thumb { position: relative; padding: 0; border: 2px solid var(--wm-border); border-radius: 8px; background: #f6f7fb; cursor: pointer; overflow: hidden; }
.viewer-thumb.is-active { border-color: var(--wm-primary); }
.viewer-thumb img { display: block; width: 100%; height: 96px; object-fit: cover; }
.viewer-thumb__label { display: block; padding: 3px 0; font-size: 10px; color: var(--wm-text-secondary); background: #fff; }
.viewer-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; color: var(--wm-text-secondary); font-size: 12px; }
.viewer-toolbar__ops { display: flex; flex-wrap: wrap; gap: 6px; }
.viewer-canvas { display: grid; place-items: center; min-height: 360px; max-height: 520px; overflow: auto; padding: 12px; border-radius: 10px; background: #f6f7fb; }
.viewer-image-wrap { position: relative; display: inline-block; line-height: 0; transition: transform 0.18s ease; }
.viewer-canvas img { max-width: 100%; max-height: 480px; object-fit: contain; }
.annotation-box { position: absolute; display: block; border: 2px solid #6366f1; box-sizing: border-box; pointer-events: auto; cursor: help; }
.annotation-box.is-ai { border-style: solid; }
.annotation-box.is-teacher { border-style: dashed; }
.viewer-meta { margin-top: 12px; }
.viewer-meta__row { display: flex; align-items: center; gap: 10px; color: var(--wm-text-secondary); font-size: 11px; }
.viewer-hint { color: var(--wm-text-secondary); font-size: 11px; }
.viewer-text { margin-top: 10px; }
.viewer-text strong { font-size: 12px; }
.viewer-text pre { margin: 6px 0 0; max-height: 200px; overflow: auto; padding: 12px; border-radius: 9px; background: #fffdf8; font-size: 12px; line-height: 1.9; white-space: pre-wrap; }
.viewer-error { margin: 8px 0 0; color: #b91c1c; font-size: 11px; }

@media (max-width: 900px) {
  .viewer-layout { grid-template-columns: 1fr; }
  .viewer-thumbs { flex-direction: row; max-height: none; overflow-x: auto; }
  .viewer-thumb { min-width: 84px; }
}
</style>