<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { buildHttpUrl } from '../utils/api'

type DefinitionKey = 'IDENTITY' | 'SOUL' | 'USER'
type DefinitionState = Record<DefinitionKey, string>

const activeDefinition = ref<DefinitionKey>('IDENTITY')
const saveStatus = ref('')
const definitionsLoaded = ref(false)
const definitions = ref<DefinitionState>({
  IDENTITY: '',
  SOUL: '',
  USER: '',
})

const currentDefinitionContent = computed({
  get: () => definitions.value[activeDefinition.value],
  set: (value: string) => {
    definitions.value[activeDefinition.value] = value
  },
})

async function loadDefinitions() {
  try {
    const response = await fetch(buildHttpUrl('/definitions'))
    if (!response.ok) {
      saveStatus.value = '加载定义失败'
      return
    }

    const payload = (await response.json()) as DefinitionState
    definitions.value = payload
    definitionsLoaded.value = true
    saveStatus.value = ''
  } catch (error) {
    console.error(error)
    saveStatus.value = '加载定义失败'
  }
}

async function saveDefinition() {
  saveStatus.value = '保存中...'
  try {
    const response = await fetch(buildHttpUrl(`/definitions/${activeDefinition.value}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: currentDefinitionContent.value }),
    })

    if (!response.ok) {
      saveStatus.value = '保存失败'
      return
    }

    const payload = (await response.json()) as {
      name: DefinitionKey
      knowledge_sync?: { updated?: boolean; chunk_count?: number } | null
    }

    if (payload.knowledge_sync) {
      const syncText = payload.knowledge_sync.updated
        ? `，并已同步知识库 ${payload.knowledge_sync.chunk_count ?? 0} 段`
        : '，知识库内容未变化，跳过重切分'
      saveStatus.value = `${payload.name} 已保存${syncText}`
      return
    }

    saveStatus.value = `${payload.name} 已保存`
  } catch (error) {
    console.error(error)
    saveStatus.value = '保存失败'
  }
}

onMounted(loadDefinitions)
</script>

<template>
  <main class="content content--config">
    <section class="content__header">
      <div>
        <h1>定义编辑</h1>
        <p>保存 SOUL 和 USER 时会自动同步到数据库知识库，内容未变化时不会重新切分。</p>
      </div>
      <div class="status-card">{{ saveStatus || '选择定义后即可编辑并保存' }}</div>
    </section>

    <section class="config-panel">
      <div class="config-tabs">
        <button
          v-for="definitionName in ['IDENTITY', 'SOUL', 'USER']"
          :key="definitionName"
          class="config-tab"
          :class="{ 'config-tab--active': activeDefinition === definitionName }"
          type="button"
          @click="activeDefinition = definitionName as DefinitionKey"
        >
          {{ definitionName }}
        </button>
      </div>

      <textarea v-model="currentDefinitionContent" class="config-editor" spellcheck="false"></textarea>

      <div class="config-actions">
        <span class="config-hint">{{ definitionsLoaded ? '定义已加载' : '正在加载定义...' }}</span>
        <button class="secondary-button" type="button" @click="loadDefinitions">重新加载</button>
        <button class="primary-button" type="button" @click="saveDefinition">保存</button>
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
  height: 100%;
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

.config-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 16px;
  min-height: 0;
  padding: 18px;
  border: 1px solid rgba(217, 119, 6, 0.14);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 45px rgba(180, 83, 9, 0.08);
  backdrop-filter: blur(18px);
}

.config-tabs {
  display: flex;
  gap: 10px;
}

.config-tab {
  height: 40px;
  padding: 0 18px;
  border: 1px solid rgba(217, 119, 6, 0.16);
  border-radius: 12px;
  background: #fff;
  color: #7c5c2f;
  cursor: pointer;
}

.config-tab--active {
  background: linear-gradient(135deg, #ffedd5 0%, #fed7aa 100%);
  color: #c2410c;
  font-weight: 700;
}

.config-editor {
  width: 100%;
  min-height: 0;
  padding: 18px;
  resize: none;
  border: 1px solid rgba(217, 119, 6, 0.14);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  color: #374151;
  font-family: Consolas, "Courier New", monospace;
  line-height: 1.7;
}

.config-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-hint {
  margin-right: auto;
  color: #9a6b36;
  font-size: 13px;
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
</style>
