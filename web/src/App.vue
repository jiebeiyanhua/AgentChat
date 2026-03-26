<script setup lang="ts">
import { computed, ref } from 'vue'

import ChatView from './views/ChatView.vue'
import ConfigView from './views/ConfigView.vue'
import KnowledgeView from './views/KnowledgeView.vue'

type ViewMode = 'chat' | 'config' | 'knowledge'

const activeView = ref<ViewMode>('chat')

const currentView = computed(() => {
  if (activeView.value === 'config') return ConfigView
  if (activeView.value === 'knowledge') return KnowledgeView
  return ChatView
})
</script>

<template>
  <div class="dashboard-shell">
    <aside class="sidebar">
      <div class="sidebar__brand">
        <div class="brand-mark">AI</div>
        <div class="brand-copy">
          <div class="brand-copy__name">PYAI</div>
          <div class="brand-copy__sub">控制台</div>
        </div>
      </div>

      <div class="sidebar__scroll">
        <section class="nav-group">
          <div class="nav-group__title">工作区</div>
          <button class="nav-item" :class="{ 'nav-item--active': activeView === 'chat' }" type="button" @click="activeView = 'chat'">
            <span>聊天</span>
          </button>
          <button class="nav-item" :class="{ 'nav-item--active': activeView === 'config' }" type="button" @click="activeView = 'config'">
            <span>定义编辑</span>
          </button>
          <button class="nav-item" :class="{ 'nav-item--active': activeView === 'knowledge' }" type="button" @click="activeView = 'knowledge'">
            <span>知识库</span>
          </button>
        </section>
      </div>
    </aside>

    <section class="workspace">
      <component :is="currentView" />
    </section>
  </div>
</template>

<style>
:root {
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: #101828;
  background: #fffaf5;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 1100px;
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(255, 214, 153, 0.35), transparent 28%),
    linear-gradient(180deg, #fffaf5 0%, #fff 52%, #fff7ed 100%);
  color: #1f2937;
}

button,
input,
textarea {
  font: inherit;
}

#app {
  min-height: 100vh;
}

.dashboard-shell {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(217, 119, 6, 0.12);
  background: rgba(255, 251, 235, 0.88);
  backdrop-filter: blur(12px);
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 64px;
  padding: 0 18px;
  border-bottom: 1px solid rgba(217, 119, 6, 0.12);
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f97316 0%, #dc2626 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
}

.brand-copy__name {
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.brand-copy__sub {
  font-size: 12px;
  color: #9a6b36;
}

.sidebar__scroll {
  flex: 1;
  overflow: auto;
  padding: 18px 12px;
}

.nav-group__title {
  margin: 0 10px 10px;
  color: #a16207;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.nav-item {
  width: 100%;
  margin-bottom: 8px;
  padding: 12px 14px;
  border: none;
  border-radius: 14px;
  background: transparent;
  color: #7c5c2f;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.nav-item:hover {
  background: rgba(251, 191, 36, 0.12);
  transform: translateX(2px);
}

.nav-item--active {
  background: linear-gradient(135deg, rgba(249, 115, 22, 0.14), rgba(220, 38, 38, 0.12));
  color: #c2410c;
  font-weight: 700;
}

.workspace {
  min-width: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

@media (max-width: 1200px) {
  body {
    min-width: 960px;
  }
}
</style>
