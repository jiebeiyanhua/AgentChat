<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { buildHttpUrl } from '../utils/api'

interface McpServerStatus {
  name: string
  transport: string
  status: string
  tool_count: number
  tools: string[]
  error: string | null
  url: string | null
  command: string | null
  args: string[]
}

interface McpConfigPayload {
  fail_fast?: boolean
  servers?: Array<Record<string, unknown>>
}

const mcpStatus = ref('')
const configStatus = ref('')
const configPath = ref('')
const configText = ref('')
const loadingMcp = ref(false)
const savingConfig = ref(false)
const servers = ref<McpServerStatus[]>([])

const connectedCount = computed(() => servers.value.filter((item) => item.status === 'connected').length)
const availableToolCount = computed(() => servers.value.reduce((sum, item) => sum + item.tool_count, 0))

function normalizeStatus(status: string) {
  if (status === 'connected') return '已连接'
  if (status === 'error') return '连接失败'
  if (status === 'closed') return '已关闭'
  if (status === 'pending') return '连接中'
  return status || '未知'
}

function getStatusClass(status: string) {
  if (status === 'connected') return 'status-pill status-pill--connected'
  if (status === 'error') return 'status-pill status-pill--error'
  return 'status-pill status-pill--muted'
}

function getEndpointLabel(server: McpServerStatus) {
  if (server.url) return server.url
  if (server.command) return [server.command, ...server.args].join(' ')
  return '--'
}

async function loadMcpServers() {
  const response = await fetch(buildHttpUrl('/mcp/servers'))
  if (!response.ok) {
    throw new Error('加载 MCP 状态失败')
  }

  const payload = (await response.json()) as { servers: McpServerStatus[] }
  servers.value = payload.servers
  mcpStatus.value = payload.servers.length
    ? `已加载 ${payload.servers.length} 个 MCP 扩展`
    : '当前未配置 MCP 扩展'
}

async function loadMcpConfig() {
  const response = await fetch(buildHttpUrl('/mcp/config'))
  if (!response.ok) {
    throw new Error('加载 MCP 配置失败')
  }

  const payload = (await response.json()) as { config_path: string; config: McpConfigPayload }
  configPath.value = payload.config_path
  configText.value = JSON.stringify(payload.config, null, 2)
  configStatus.value = '配置已加载'
}

async function refreshPageData() {
  loadingMcp.value = true
  try {
    await Promise.all([loadMcpServers(), loadMcpConfig()])
  } catch (error) {
    console.error(error)
    const message = error instanceof Error ? error.message : '加载 MCP 信息失败'
    mcpStatus.value = message
    configStatus.value = message
  } finally {
    loadingMcp.value = false
  }
}

async function saveMcpConfig() {
  if (savingConfig.value) return

  let parsedConfig: McpConfigPayload
  try {
    parsedConfig = JSON.parse(configText.value) as McpConfigPayload
  } catch (error) {
    console.error(error)
    configStatus.value = 'JSON 格式不正确，保存失败'
    return
  }

  savingConfig.value = true
  configStatus.value = '正在保存并重载 MCP...'

  try {
    const response = await fetch(buildHttpUrl('/mcp/config'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config: parsedConfig }),
    })

    if (!response.ok) {
      const errorPayload = (await response.json().catch(() => null)) as { detail?: string } | null
      configStatus.value = errorPayload?.detail || '保存失败'
      return
    }

    const payload = (await response.json()) as {
      config_path: string
      config: McpConfigPayload
      servers: McpServerStatus[]
    }
    configPath.value = payload.config_path
    configText.value = JSON.stringify(payload.config, null, 2)
    servers.value = payload.servers
    configStatus.value = 'MCP 配置已保存并生效'
    mcpStatus.value = payload.servers.length
      ? `已更新 ${payload.servers.length} 个 MCP 扩展状态`
      : '当前未配置 MCP 扩展'
  } catch (error) {
    console.error(error)
    configStatus.value = '保存失败'
  } finally {
    savingConfig.value = false
  }
}

onMounted(refreshPageData)
</script>

<template>
  <main class="content content--mcp">
    <section class="content__header">
      <div>
        <h1>MCP 扩展</h1>
        <p>这里可以直接编辑 `mcp` 配置并查看生效后的连接状态与工具列表，适合管理钉钉、飞书等扩展。</p>
      </div>
      <div class="status-card">{{ mcpStatus || '支持保存后自动重连 MCP' }}</div>
    </section>

    <section class="config-panel">
      <div class="config-panel__head">
        <div>
          <h2>MCP 配置</h2>
          <p>当前配置文件：{{ configPath || '--' }}</p>
        </div>
        <div class="config-panel__actions">
          <span class="config-hint">{{ configStatus || '编辑后点击保存即可应用' }}</span>
          <button class="secondary-button" type="button" :disabled="loadingMcp || savingConfig" @click="refreshPageData">重新加载</button>
          <button class="primary-button" type="button" :disabled="savingConfig" @click="saveMcpConfig">
            {{ savingConfig ? '保存中' : '保存并应用' }}
          </button>
        </div>
      </div>

      <textarea v-model="configText" class="config-editor" spellcheck="false"></textarea>
    </section>

    <section class="guide-panel">
      <div class="guide-panel__head">
        <h2>使用说明</h2>
        <p>每次保存都会写入 `mcp` 配置、重新初始化 MCP 连接，并在下方状态区展示结果。</p>
      </div>

      <div class="guide-grid">
        <article class="guide-card">
          <h3>基础结构</h3>
          <p>`mcp` 下建议包含 `fail_fast` 和 `servers` 两个字段。</p>
          <pre class="guide-code"><code>{
  "fail_fast": false,
  "servers": []
}</code></pre>
        </article>

        <article class="guide-card">
          <h3>通用字段</h3>
          <p>每个 server 至少要有 `name` 和 `transport`。</p>
          <ul class="guide-list">
            <li>`name`：扩展名称，必须唯一。</li>
            <li>`transport`：支持 `stdio`、`sse`、`streamable_http`。</li>
            <li>`enabled`：可选，设为 `false` 时启动会跳过该扩展。</li>
          </ul>
        </article>

        <article class="guide-card">
          <h3>stdio 用法</h3>
          <p>适合本地命令启动的 MCP server，例如通过 `npx`、`uvx`、`python` 启动。</p>
          <pre class="guide-code"><code>{
  "name": "feishu",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "your-feishu-mcp-server"],
  "env": {
    "FEISHU_APP_ID": "xxx",
    "FEISHU_APP_SECRET": "xxx"
  }
}</code></pre>
        </article>

        <article class="guide-card">
          <h3>HTTP / SSE 用法</h3>
          <p>适合远程托管的 MCP 服务，通常填写 URL 和认证头。</p>
          <pre class="guide-code"><code>{
  "name": "dingtalk",
  "transport": "streamable_http",
  "url": "https://your-dingtalk-mcp.example.com/mcp",
  "headers": {
    "Authorization": "Bearer your-token"
  }
}</code></pre>
        </article>

        <article class="guide-card">
          <h3>保存后怎么看结果</h3>
          <ul class="guide-list">
            <li>状态为“已连接”表示初始化成功。</li>
            <li>状态为“连接失败”时，错误原因会显示在对应卡片里。</li>
            <li>工具列表不为空时，说明该 MCP 已经向 Agent 暴露可用工具。</li>
          </ul>
        </article>

        <article class="guide-card">
          <h3>常见注意点</h3>
          <ul class="guide-list">
            <li>`name` 不能重复。</li>
            <li>`stdio` 需要填写 `command`，HTTP/SSE 需要填写 `url`。</li>
            <li>如果某个扩展经常初始化失败，可以先把 `enabled` 设为 `false`。</li>
            <li>`fail_fast=true` 时，只要有一个扩展初始化失败，启动就会直接报错。</li>
          </ul>
        </article>
      </div>
    </section>

    <section class="summary-grid">
      <article class="summary-card">
        <span class="summary-card__label">扩展总数</span>
        <strong class="summary-card__value">{{ servers.length }}</strong>
      </article>
      <article class="summary-card">
        <span class="summary-card__label">已连接</span>
        <strong class="summary-card__value">{{ connectedCount }}</strong>
      </article>
      <article class="summary-card">
        <span class="summary-card__label">可用工具</span>
        <strong class="summary-card__value">{{ availableToolCount }}</strong>
      </article>
      <article class="summary-card summary-card--action">
        <button class="primary-button" type="button" :disabled="loadingMcp" @click="loadMcpServers">
          {{ loadingMcp ? '刷新中' : '刷新状态' }}
        </button>
      </article>
    </section>

    <section class="server-list">
      <article v-for="server in servers" :key="server.name" class="server-card">
        <div class="server-card__head">
          <div>
            <div class="server-card__title">
              <h2>{{ server.name }}</h2>
              <span class="transport-tag">{{ server.transport }}</span>
            </div>
            <div class="server-card__endpoint">{{ getEndpointLabel(server) }}</div>
          </div>
          <span :class="getStatusClass(server.status)">{{ normalizeStatus(server.status) }}</span>
        </div>

        <div class="server-card__meta">
          <span>工具数：{{ server.tool_count }}</span>
        </div>

        <div v-if="server.error" class="error-box">{{ server.error }}</div>

        <div class="tool-section">
          <div class="tool-section__title">可用工具</div>
          <div v-if="server.tools.length" class="tool-list">
            <span v-for="toolName in server.tools" :key="toolName" class="tool-chip">{{ toolName }}</span>
          </div>
          <div v-else class="empty-state">当前没有可用工具</div>
        </div>
      </article>

      <div v-if="!servers.length" class="empty-panel">
        <strong>当前没有 MCP 扩展</strong>
        <span>先在上面的 JSON 编辑器里补充 `servers`，保存后这里会自动更新。</span>
      </div>
    </section>
  </main>
</template>

<style scoped>
.content {
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  gap: 18px;
  padding: 22px;
  min-height: 0;
  height: 100%;
}

.content__header,
.config-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.content__header h1,
.config-panel__head h2 {
  margin: 0;
  line-height: 1.05;
}

.content__header h1 {
  font-size: 32px;
}

.config-panel__head h2 {
  font-size: 24px;
}

.content__header p,
.config-panel__head p {
  margin: 8px 0 0;
  color: #7c5c2f;
  font-size: 14px;
  line-height: 1.7;
}

.content__header p {
  max-width: 780px;
}

.status-card,
.config-hint {
  color: #7c5c2f;
  font-size: 13px;
  line-height: 1.5;
}

.status-card {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 10px 16px;
  border: 1px solid rgba(217, 119, 6, 0.16);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  max-width: 420px;
}

.config-panel,
.summary-card,
.server-card {
  border: 1px solid rgba(217, 119, 6, 0.14);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 18px 45px rgba(180, 83, 9, 0.08);
  backdrop-filter: blur(18px);
}

.config-panel {
  display: grid;
  gap: 16px;
  padding: 18px;
  border-radius: 24px;
}

.config-panel__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-hint {
  max-width: 340px;
}

.config-editor {
  width: 100%;
  min-height: 280px;
  padding: 18px;
  resize: vertical;
  border: 1px solid rgba(217, 119, 6, 0.14);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  color: #374151;
  font-family: Consolas, "Courier New", monospace;
  line-height: 1.7;
}

.guide-panel {
  display: grid;
  gap: 16px;
  padding: 18px;
  border: 1px solid rgba(217, 119, 6, 0.14);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 18px 45px rgba(180, 83, 9, 0.08);
  backdrop-filter: blur(18px);
}

.guide-panel__head h2,
.guide-card h3 {
  margin: 0;
}

.guide-panel__head p,
.guide-card p {
  margin: 8px 0 0;
  color: #7c5c2f;
  font-size: 13px;
  line-height: 1.7;
}

.guide-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.guide-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(217, 119, 6, 0.14);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 247, 237, 0.92));
}

.guide-list {
  margin: 0;
  padding-left: 18px;
  color: #7c5c2f;
  font-size: 13px;
  line-height: 1.8;
}

.guide-code {
  margin: 0;
  padding: 14px;
  overflow: auto;
  border-radius: 14px;
  background: #1f2937;
  color: #f8fafc;
  font-size: 12px;
  line-height: 1.7;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  display: grid;
  gap: 10px;
  padding: 18px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 247, 237, 0.92));
}

.summary-card__label {
  color: #9a6b36;
  font-size: 13px;
}

.summary-card__value {
  font-size: 32px;
  line-height: 1;
  color: #c2410c;
}

.summary-card--action {
  display: flex;
  align-items: center;
  justify-content: center;
}

.server-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.server-card {
  display: grid;
  gap: 14px;
  padding: 18px;
  border-radius: 24px;
}

.server-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.server-card__title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.server-card__title h2 {
  margin: 0;
  font-size: 22px;
}

.server-card__endpoint,
.server-card__meta {
  color: #7c5c2f;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-all;
}

.transport-tag,
.tool-chip,
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.transport-tag {
  padding: 5px 10px;
  background: #ffedd5;
  color: #c2410c;
  text-transform: lowercase;
}

.status-pill {
  min-width: 74px;
  padding: 6px 12px;
}

.status-pill--connected {
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
}

.status-pill--error {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.status-pill--muted {
  background: rgba(148, 163, 184, 0.16);
  color: #475569;
}

.tool-section {
  display: grid;
  gap: 10px;
}

.tool-section__title {
  font-size: 13px;
  font-weight: 700;
  color: #9a6b36;
}

.tool-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tool-chip {
  padding: 7px 12px;
  background: rgba(251, 191, 36, 0.14);
  color: #9a3412;
}

.error-box,
.empty-state,
.empty-panel {
  border-radius: 16px;
  font-size: 13px;
  line-height: 1.7;
}

.error-box {
  padding: 12px 14px;
  background: rgba(254, 242, 242, 0.95);
  color: #b91c1c;
  border: 1px solid rgba(239, 68, 68, 0.18);
  word-break: break-word;
}

.empty-state {
  padding: 12px 14px;
  background: rgba(255, 251, 235, 0.7);
  color: #9a6b36;
}

.empty-panel {
  display: grid;
  gap: 8px;
  padding: 24px;
  border: 1px dashed rgba(217, 119, 6, 0.3);
  background: rgba(255, 251, 235, 0.7);
  color: #7c5c2f;
}

.primary-button,
.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 42px;
  padding: 0 18px;
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

@media (max-width: 1200px) {
  .guide-grid,
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .config-panel__head {
    flex-direction: column;
  }

  .config-panel__actions {
    width: 100%;
    flex-wrap: wrap;
  }
}

@media (max-width: 760px) {
  .guide-grid,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .server-card__head {
    flex-direction: column;
  }
}
</style>
