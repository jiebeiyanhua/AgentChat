<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'

import { buildHttpUrl } from '../utils/api'
import { wsService } from '../utils/websocket'

type ChatRole = 'user' | 'assistant' | 'system'

interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  timestamp: string
  pending?: boolean
}

interface HistoryMessage {
  id?: string | null
  role: ChatRole
  content: string
  timestamp: string
}

const defaultSessionId = () => `session-${Math.random().toString(36).slice(2, 10)}`

const storedSessionId = localStorage.getItem('pyai_session_id')
const sessionId = ref(storedSessionId || defaultSessionId())

// 保存session_id到localStorage
if (!storedSessionId) {
  localStorage.setItem('pyai_session_id', sessionId.value)
}

const inputText = ref('')
const messages = ref<ChatMessage[]>([])

const messageListRef = ref<HTMLElement | null>(null)
let currentAssistantMessageId = ''

const canSend = computed(() => Boolean(inputText.value.trim()) && !wsService.state.isStreaming)
const shortWsUrl = computed(() => (wsService.wsUrl.value.length > 42 ? `${wsService.wsUrl.value.slice(0, 42)}...` : wsService.wsUrl.value))
const connectionBadge = computed(() => {
  if (wsService.state.isStreaming) return { tone: 'warn', label: '生成中' }
  if (wsService.state.isConnected) return { tone: 'ok', label: '已连接' }
  return { tone: 'danger', label: '未连接' }
})

function nowIso() {
  return new Date().toISOString()
}

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

function summarizeSystemMessage(content: string) {
  const cleanContent = content.replace(/\s+/g, ' ').trim()
  if (!cleanContent) return ''

  if (cleanContent.toLowerCase().includes('retrieve_profile')) {
    return '知识库检索'
  }

  return '工具调用'
}

function toDisplayMessage(message: HistoryMessage): ChatMessage {
  return {
    id: message.id ?? crypto.randomUUID(),
    role: message.role,
    content: message.role === 'system' ? summarizeSystemMessage(message.content) : message.content,
    timestamp: message.timestamp || nowIso(),
    pending: false,
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (!messageListRef.value) return
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  })
}

function pushMessage(role: ChatRole, content: string, pending = false, timestamp = nowIso()) {
  const displayContent = role === 'system' ? summarizeSystemMessage(content) : content
  if (role === 'system' && !displayContent) return

  messages.value.push({
    id: crypto.randomUUID(),
    role,
    content: displayContent,
    pending,
    timestamp,
  })
  scrollToBottom()
}

function ensureAssistantMessage() {
  const lastMessage = messages.value.at(-1)
  if (lastMessage?.role === 'assistant' && lastMessage.pending) {
    currentAssistantMessageId = lastMessage.id
    return lastMessage
  }

  const assistantMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: '',
    pending: true,
    timestamp: nowIso(),
  }
  currentAssistantMessageId = assistantMessage.id
  messages.value.push(assistantMessage)
  scrollToBottom()
  return assistantMessage
}

function finalizeAssistantMessage() {
  const target = messages.value.find((message) => message.id === currentAssistantMessageId)
  if (!target) return
  target.pending = false
  if (!target.content.trim()) target.content = '本次没有可显示内容。'
}

async function loadHistory() {
  try {
    const response = await fetch(buildHttpUrl('/agent-history', { session_id: sessionId.value }))
    if (!response.ok) return

    const payload = (await response.json()) as { messages: HistoryMessage[] }
    messages.value = payload.messages
      .map(toDisplayMessage)
      .filter((message) => message.role !== 'system' || Boolean(message.content))
    scrollToBottom()
  } catch (error) {
    console.error(error)
  }
}

function handleSocketMessage(payload: any) {
  if (payload.type === 'chunk') {
    wsService.state.isStreaming = true
    wsService.state.statusText = 'streaming'
    ensureAssistantMessage().content += payload.content ?? ''
    scrollToBottom()
    return
  }

  if (payload.type === 'action') {
    pushMessage('system', payload.content ?? 'Tool action')
    return
  }

  if (payload.type === 'error') {
    wsService.state.isStreaming = false
    wsService.state.statusText = wsService.state.isConnected ? 'connected' : 'error'
    finalizeAssistantMessage()
    return
  }

  if (payload.type === 'done') {
    wsService.state.isStreaming = false
    wsService.state.statusText = 'connected'
    finalizeAssistantMessage()
    return
  }

  if (payload.type === 'heartbeat_ack') {
    wsService.state.statusText = wsService.state.isStreaming ? 'streaming' : 'connected'
  }
}

function connectSocket() {
  wsService.connect()
}

function disconnectSocket() {
  wsService.disconnect()
}

function sendMessage() {
  if (!canSend.value || !wsService.state.isConnected) return

  const content = inputText.value.trim()
  pushMessage('user', content)
  inputText.value = ''
  wsService.state.isStreaming = true
  wsService.state.statusText = 'streaming'
  currentAssistantMessageId = ''

  wsService.send({ input_text: content })
}

function resetSession() {
  const newSessionId = defaultSessionId()
  sessionId.value = newSessionId
  localStorage.setItem('pyai_session_id', newSessionId)
  wsService.setSessionId(newSessionId)
  messages.value = []
  inputText.value = ''
  currentAssistantMessageId = ''
  scrollToBottom()
}

function handleTextareaKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

// 监听sessionId变化，更新WebSocket服务的sessionId
watch(sessionId, (newSessionId) => {
  wsService.setSessionId(newSessionId)
})

onMounted(() => {
  // 设置sessionId和消息回调
  wsService.setSessionId(sessionId.value)
  wsService.setMessageCallback(handleSocketMessage)
  
  // 无论是否连接，都先加载历史记录
  loadHistory()
  
  // 如果还没有连接，尝试连接
  if (!wsService.state.isConnected) {
    wsService.connect()
  }
})

onBeforeUnmount(() => {
  // 清理回调
  wsService.setMessageCallback(null)
})
</script>

<template>
  <main class="content">
    <section class="content__header">
      <div>
        <h1>聊天</h1>
        <p>连接后即可与当前智能体会话，工具调用会显示为系统消息。</p>
      </div>
      <div class="status-stack">
        <div class="badge-row">
          <div class="badge-pill badge-pill--neutral badge-pill--wide">
            <span class="badge-pill__dot"></span>
            <span>连接地址 {{ shortWsUrl }}</span>
          </div>
          <div class="badge-pill" :class="`badge-pill--${connectionBadge.tone}`">
            <span class="badge-pill__dot"></span>
            <span>{{ connectionBadge.label }}</span>
          </div>
        </div>
        <div class="status-row">
          <div class="topbar__session">
            <span class="topbar__session-label">会话</span>
            <span class="topbar__session-value">{{ sessionId }}</span>
          </div>
          <button class="secondary-button" type="button" @click="resetSession">新会话</button>
          <button class="primary-button" type="button" @click="wsService.state.isConnected ? disconnectSocket() : connectSocket()">
            {{ wsService.state.isConnected ? '断开' : '连接' }}
          </button>
        </div>
      </div>
    </section>

    <section ref="messageListRef" class="chat-panel">
      <template v-for="message in messages" :key="message.id">
        <div class="time-divider">{{ formatTime(message.timestamp) }}</div>
        <article class="chat-row" :class="`chat-row--${message.role}`">
          <div v-if="message.role !== 'system'" class="avatar" :class="`avatar--${message.role}`">
            {{ message.role === 'user' ? '你' : 'AI' }}
          </div>
          <div class="chat-bubble" :class="`chat-bubble--${message.role}`">
            <div class="chat-bubble__body">{{ message.content }}</div>
          </div>
        </article>
      </template>
    </section>

    <footer class="composer-bar">
      <textarea
        v-model="inputText"
        class="composer-bar__input"
        rows="2"
        placeholder="输入问题后回车发送，Shift + Enter 换行"
        @keydown="handleTextareaKeydown"
      />
      <button class="primary-button" type="button" :disabled="!canSend || !wsService.state.isConnected" @click="sendMessage">
        {{ wsService.state.isStreaming ? '发送中' : '发送' }}
      </button>
    </footer>
  </main>
</template>

<style scoped>
.content {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
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

.status-stack {
  display: grid;
  gap: 10px;
}

.badge-row,
.status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.badge-pill,
.topbar__session {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid rgba(217, 119, 6, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #7c5c2f;
  font-size: 13px;
}

.badge-pill--wide {
  max-width: 360px;
}

.badge-pill__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d97706;
}

.badge-pill--ok .badge-pill__dot {
  background: #22c55e;
}

.badge-pill--warn .badge-pill__dot {
  background: #f59e0b;
}

.badge-pill--danger .badge-pill__dot {
  background: #ef4444;
}

.topbar__session-label {
  color: #a16207;
  font-size: 12px;
}

.topbar__session-value {
  max-width: 180px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.chat-panel {
  min-height: 0;
  overflow: auto;
  padding: 14px 16px 20px;
  border: 1px solid rgba(217, 119, 6, 0.14);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 45px rgba(180, 83, 9, 0.08);
  backdrop-filter: blur(18px);
}

.time-divider {
  margin: 18px auto 10px;
  width: fit-content;
  color: #9a6b36;
  font-size: 12px;
}

.chat-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 10px;
}

.chat-row--user {
  justify-content: flex-end;
}

.avatar {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  flex: 0 0 36px;
}

.avatar--assistant {
  background: #ffedd5;
  color: #c2410c;
}

.avatar--user {
  order: 2;
  background: #dbeafe;
  color: #1d4ed8;
}

.chat-bubble {
  max-width: 72%;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(217, 119, 6, 0.12);
  background: #fff;
  color: #374151;
}

.chat-bubble--user {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
}

.chat-bubble--system {
  max-width: 280px;
  margin: 0 auto;
  border-style: dashed;
  color: #9a6b36;
  background: #fffbeb;
  font-size: 13px;
}

.chat-bubble__body {
  white-space: pre-wrap;
  line-height: 1.75;
}

.composer-bar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 100px;
  gap: 12px;
  align-items: end;
}

.composer-bar__input {
  width: 100%;
  min-height: 68px;
  padding: 16px;
  resize: none;
  border: 1px solid rgba(217, 119, 6, 0.14);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  color: #374151;
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
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.primary-button:hover,
.secondary-button:hover {
  transform: translateY(-1px);
}

.primary-button:disabled,
.secondary-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
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
