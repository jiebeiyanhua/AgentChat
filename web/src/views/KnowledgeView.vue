<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { buildHttpUrl } from '../utils/api'

interface KnowledgeSource {
  source_key: string
  source_name: string
  source_type: string
  file_path: string | null
  chunk_count: number
  updated_at: string | null
}

interface KnowledgeUploadResult {
  source_name: string
  chunk_count?: number
  updated?: boolean
}

const knowledgeStatus = ref('')
const uploadingKnowledge = ref(false)
const selectedKnowledgeFile = ref<File | null>(null)
const knowledgeSources = ref<KnowledgeSource[]>([])

function formatTime(timestamp: string | null) {
  if (!timestamp) return '--'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return '--'

  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

async function loadKnowledgeSources() {
  try {
    const response = await fetch(buildHttpUrl('/knowledge-sources'))
    if (!response.ok) {
      knowledgeStatus.value = '加载知识库列表失败'
      return
    }

    const payload = (await response.json()) as { sources: KnowledgeSource[] }
    knowledgeSources.value = payload.sources
    if (!knowledgeStatus.value.includes('失败')) {
      knowledgeStatus.value = `共 ${payload.sources.length} 个知识库来源`
    }
  } catch (error) {
    console.error(error)
    knowledgeStatus.value = '加载知识库列表失败'
  }
}

function handleKnowledgeFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  selectedKnowledgeFile.value = target.files?.[0] ?? null
}

async function uploadKnowledgeFile() {
  if (!selectedKnowledgeFile.value || uploadingKnowledge.value) return

  uploadingKnowledge.value = true
  knowledgeStatus.value = `正在上传 ${selectedKnowledgeFile.value.name}...`

  try {
    const formData = new FormData()
    formData.append('file', selectedKnowledgeFile.value)

    const response = await fetch(buildHttpUrl('/knowledge-sources/upload'), {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorPayload = (await response.json().catch(() => null)) as { detail?: string } | null
      knowledgeStatus.value = errorPayload?.detail || '上传失败'
      return
    }

    const payload = (await response.json()) as KnowledgeUploadResult
    knowledgeStatus.value = payload.updated
      ? `${payload.source_name} 已入库，共 ${payload.chunk_count ?? 0} 段`
      : `${payload.source_name} 内容未变化，跳过重新切分`
    selectedKnowledgeFile.value = null

    const fileInput = document.getElementById('knowledge-upload-input') as HTMLInputElement | null
    if (fileInput) fileInput.value = ''

    await loadKnowledgeSources()
  } catch (error) {
    console.error(error)
    knowledgeStatus.value = '上传失败'
  } finally {
    uploadingKnowledge.value = false
  }
}

onMounted(loadKnowledgeSources)
</script>

<template>
  <main class="content content--knowledge">
    <section class="content__header">
      <div>
        <h1>知识库</h1>
        <p>上传文本或 Markdown 文件后会自动切分，并将分片文本写入数据库供知识库检索工具使用。</p>
      </div>
      <div class="status-card">{{ knowledgeStatus || '支持重复上传，同名文件会覆盖旧内容' }}</div>
    </section>

    <section class="knowledge-panel">
      <div class="upload-card">
        <label class="upload-input" for="knowledge-upload-input">
          <input id="knowledge-upload-input" type="file" accept=".txt,.md,.markdown,.text" @change="handleKnowledgeFileChange" />
          <span>{{ selectedKnowledgeFile?.name || '选择知识库文件' }}</span>
        </label>
        <button class="secondary-button" type="button" @click="loadKnowledgeSources">刷新列表</button>
        <button class="primary-button" type="button" :disabled="!selectedKnowledgeFile || uploadingKnowledge" @click="uploadKnowledgeFile">
          {{ uploadingKnowledge ? '上传中' : '上传入库' }}
        </button>
      </div>

      <div class="knowledge-list">
        <article v-for="source in knowledgeSources" :key="source.source_key" class="knowledge-item">
          <div class="knowledge-item__head">
            <strong>{{ source.source_name }}</strong>
            <span class="source-tag">{{ source.source_type }}</span>
          </div>
          <div class="knowledge-item__meta">分片数：{{ source.chunk_count }}</div>
          <div class="knowledge-item__meta">更新时间：{{ formatTime(source.updated_at) }}</div>
          <div class="knowledge-item__meta">来源：{{ source.file_path || source.source_key }}</div>
        </article>
      </div>
    </section>
  </main>
</template>

<style scoped>
.content {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
  padding: 22px;
  min-height: 0;
}

.content__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.content__header h1 {
  margin: 0;
  font-size: 32px;
  line-height: 1.05;
}

.content__header p {
  margin: 8px 0 0;
  color: #7c5c2f;
  font-size: 14px;
  max-width: 760px;
  line-height: 1.7;
}

.status-card {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 10px 16px;
  border: 1px solid rgba(217, 119, 6, 0.16);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  color: #7c5c2f;
  font-size: 13px;
  line-height: 1.5;
  max-width: 420px;
}

.knowledge-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
  min-height: 0;
  padding: 18px;
  border: 1px solid rgba(217, 119, 6, 0.14);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 45px rgba(180, 83, 9, 0.08);
  backdrop-filter: blur(18px);
}

.upload-card {
  display: flex;
  align-items: center;
  gap: 12px;
}

.upload-input {
  display: inline-flex;
  align-items: center;
  min-width: 320px;
  padding: 0 14px;
  height: 42px;
  border: 1px dashed rgba(217, 119, 6, 0.4);
  border-radius: 14px;
  background: #fffbeb;
  color: #7c5c2f;
  cursor: pointer;
}

.upload-input input {
  display: none;
}

.knowledge-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
  overflow: auto;
  padding-right: 4px;
}

.knowledge-item {
  padding: 16px;
  border: 1px solid rgba(217, 119, 6, 0.14);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 247, 237, 0.92));
}

.knowledge-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.knowledge-item__meta {
  color: #7c5c2f;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-all;
}

.source-tag {
  padding: 4px 8px;
  border-radius: 999px;
  background: #ffedd5;
  color: #c2410c;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.primary-button,
.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  padding: 0 16px;
  border-radius: 12px;
  cursor: pointer;
  border: 1px solid rgba(217, 119, 6, 0.16);
}

.secondary-button {
  background: #fff;
  color: #7c5c2f;
}

.primary-button {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: #fff;
}

.primary-button:disabled,
.secondary-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
