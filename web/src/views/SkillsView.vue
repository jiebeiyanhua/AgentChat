<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { buildHttpUrl } from '../utils/api'

interface SkillInfo {
  name: string
  directory: string
  skill_file: string
  title: string
  description: string
  updated_at: string | null
}

const skills = ref<SkillInfo[]>([])
const skillsDir = ref('')
const skillsStatus = ref('')
const installUrl = ref('')
const installName = ref('')
const selectedZipFile = ref<File | null>(null)
const loadingSkills = ref(false)
const installingSkill = ref(false)
const uploadingSkill = ref(false)

const installedCount = computed(() => skills.value.length)

async function loadSkills() {
  loadingSkills.value = true
  try {
    const response = await fetch(buildHttpUrl('/skills'))
    if (!response.ok) {
      skillsStatus.value = '加载技能列表失败'
      return
    }

    const payload = (await response.json()) as { skills_dir: string; skills: SkillInfo[] }
    skillsDir.value = payload.skills_dir
    skills.value = payload.skills
    if (!skillsStatus.value.includes('失败')) {
      skillsStatus.value = payload.skills.length ? `已安装 ${payload.skills.length} 个 skill` : '当前还没有已下载的 skill'
    }
  } catch (error) {
    console.error(error)
    skillsStatus.value = '加载技能列表失败'
  } finally {
    loadingSkills.value = false
  }
}

function handleZipFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  selectedZipFile.value = target.files?.[0] ?? null
}

async function installSkill() {
  if (!installUrl.value.trim() || installingSkill.value) return

  installingSkill.value = true
  skillsStatus.value = '正在下载并装配 skill...'

  try {
    const response = await fetch(buildHttpUrl('/skills/install'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: installUrl.value.trim(),
        name: installName.value.trim() || null,
      }),
    })

    if (!response.ok) {
      const errorPayload = (await response.json().catch(() => null)) as { detail?: string } | null
      skillsStatus.value = errorPayload?.detail || '下载 skill 失败'
      return
    }

    const payload = (await response.json()) as { installed: boolean; skill: SkillInfo }
    installUrl.value = ''
    installName.value = ''
    skillsStatus.value = `${payload.skill.title || payload.skill.name} 已下载到 skills 目录`
    await loadSkills()
  } catch (error) {
    console.error(error)
    skillsStatus.value = '下载 skill 失败'
  } finally {
    installingSkill.value = false
  }
}

async function uploadSkillZip() {
  if (!selectedZipFile.value || uploadingSkill.value) return

  uploadingSkill.value = true
  skillsStatus.value = `正在上传 ${selectedZipFile.value.name}...`

  try {
    const formData = new FormData()
    formData.append('file', selectedZipFile.value)
    formData.append('name', installName.value.trim())

    const response = await fetch(buildHttpUrl('/skills/upload'), {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorPayload = (await response.json().catch(() => null)) as { detail?: string } | null
      skillsStatus.value = errorPayload?.detail || '上传 skill 失败'
      return
    }

    const payload = (await response.json()) as { installed: boolean; skill: SkillInfo }
    selectedZipFile.value = null
    installName.value = ''
    const fileInput = document.getElementById('skill-zip-upload-input') as HTMLInputElement | null
    if (fileInput) fileInput.value = ''
    skillsStatus.value = `${payload.skill.title || payload.skill.name} 已上传到 skills 目录`
    await loadSkills()
  } catch (error) {
    console.error(error)
    skillsStatus.value = '上传 skill 失败'
  } finally {
    uploadingSkill.value = false
  }
}

onMounted(loadSkills)
</script>

<template>
  <main class="content content--skills">
    <section class="content__header">
      <div>
        <h1>Skills 技能装配</h1>
        <p>支持通过外部链接下载 skill，也支持直接上传 ZIP 压缩包，最终都会装配到本地 `skills` 目录并展示当前已安装列表。</p>
      </div>
      <div class="status-card">{{ skillsStatus || '下载或上传完成后会自动刷新列表' }}</div>
    </section>

    <section class="summary-grid">
      <article class="summary-card">
        <span class="summary-card__label">已安装 Skill</span>
        <strong class="summary-card__value">{{ installedCount }}</strong>
      </article>
      <article class="summary-card">
        <span class="summary-card__label">存放目录</span>
        <strong class="summary-card__path">{{ skillsDir || '--' }}</strong>
      </article>
    </section>

    <section class="skills-panel">
      <div class="install-card">
        <div class="install-card__head">
          <div>
            <h2>下载或上传 Skill</h2>
            <p>外链模式支持 ZIP 链接或直接指向 `SKILL.md` 的链接；上传模式当前支持 ZIP 压缩包。</p>
          </div>
          <button class="secondary-button" type="button" :disabled="loadingSkills || installingSkill || uploadingSkill" @click="loadSkills">
            {{ loadingSkills ? '刷新中' : '刷新列表' }}
          </button>
        </div>

        <div class="install-form">
          <input v-model="installUrl" class="text-input" type="url" placeholder="输入 skill 下载链接" />
          <input v-model="installName" class="text-input" type="text" maxlength="80" placeholder="可选：自定义本地目录名" />
          <button class="primary-button" type="button" :disabled="!installUrl.trim() || installingSkill || uploadingSkill" @click="installSkill">
            {{ installingSkill ? '下载中' : '下载并装配' }}
          </button>
        </div>

        <div class="upload-form">
          <label class="upload-input" for="skill-zip-upload-input">
            <input id="skill-zip-upload-input" type="file" accept=".zip,application/zip" @change="handleZipFileChange" />
            <span>{{ selectedZipFile?.name || '选择 skill ZIP 压缩包' }}</span>
          </label>
          <button class="primary-button" type="button" :disabled="!selectedZipFile || uploadingSkill || installingSkill" @click="uploadSkillZip">
            {{ uploadingSkill ? '上传中' : '上传并装配' }}
          </button>
        </div>
      </div>

      <div class="skills-list">
        <article v-for="skill in skills" :key="skill.name" class="skill-card">
          <div class="skill-card__head">
            <div>
              <h2>{{ skill.title || skill.name }}</h2>
              <div class="skill-card__name">{{ skill.name }}</div>
            </div>
            <span class="skill-tag">SKILL</span>
          </div>

          <p class="skill-card__description">{{ skill.description || '暂无描述' }}</p>
          <div class="skill-card__meta">更新时间：{{ skill.updated_at || '--' }}</div>
          <div class="skill-card__meta">目录：{{ skill.directory }}</div>
          <div class="skill-card__meta">入口：{{ skill.skill_file }}</div>
        </article>

        <div v-if="!skills.length" class="empty-panel">
          <strong>当前没有已安装的 skill</strong>
          <span>先通过上方下载或上传一个 ZIP，成功后这里会自动展示。</span>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.content {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 18px;
  padding: 22px;
  min-height: 0;
  height: 100%;
}

.content__header,
.install-card__head,
.skill-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.content__header h1,
.install-card__head h2,
.skill-card__head h2 {
  margin: 0;
  line-height: 1.05;
}

.content__header h1 {
  font-size: 32px;
}

.install-card__head h2,
.skill-card__head h2 {
  font-size: 22px;
}

.content__header p,
.install-card__head p,
.skill-card__description,
.skill-card__meta {
  color: #7c5c2f;
  line-height: 1.7;
}

.content__header p,
.install-card__head p {
  margin: 8px 0 0;
  font-size: 14px;
}

.content__header p {
  max-width: 760px;
}

.status-card,
.summary-card,
.install-card,
.skill-card {
  border: 1px solid rgba(217, 119, 6, 0.14);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 18px 45px rgba(180, 83, 9, 0.08);
  backdrop-filter: blur(18px);
}

.status-card {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 10px 16px;
  border-radius: 18px;
  color: #7c5c2f;
  font-size: 13px;
  line-height: 1.5;
  max-width: 420px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
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

.summary-card__path {
  color: #7c5c2f;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-all;
}

.skills-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
  min-height: 0;
}

.install-card,
.skill-card {
  border-radius: 24px;
}

.install-card {
  display: grid;
  gap: 16px;
  padding: 18px;
}

.install-form,
.upload-form {
  display: grid;
  gap: 12px;
}

.install-form {
  grid-template-columns: minmax(320px, 1.2fr) minmax(220px, 0.8fr) auto;
}

.upload-form {
  grid-template-columns: minmax(320px, 1fr) auto;
}

.text-input,
.upload-input {
  width: 100%;
  min-width: 0;
  height: 44px;
  padding: 0 14px;
  border-radius: 14px;
  color: #7c5c2f;
}

.text-input {
  border: 1px solid rgba(217, 119, 6, 0.16);
  background: #fff;
}

.upload-input {
  display: inline-flex;
  align-items: center;
  border: 1px dashed rgba(217, 119, 6, 0.4);
  background: #fffbeb;
  cursor: pointer;
}

.upload-input input {
  display: none;
}

.skills-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.skill-card {
  display: grid;
  gap: 12px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 247, 237, 0.92));
}

.skill-card__name {
  margin-top: 6px;
  color: #9a6b36;
  font-size: 13px;
}

.skill-card__description {
  margin: 0;
  font-size: 13px;
}

.skill-card__meta {
  font-size: 13px;
  word-break: break-all;
}

.skill-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: #ffedd5;
  color: #c2410c;
  font-size: 12px;
  font-weight: 700;
}

.empty-panel {
  display: grid;
  gap: 8px;
  padding: 24px;
  border: 1px dashed rgba(217, 119, 6, 0.3);
  border-radius: 20px;
  background: rgba(255, 251, 235, 0.7);
  color: #7c5c2f;
  font-size: 13px;
  line-height: 1.7;
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

@media (max-width: 1100px) {
  .summary-grid,
  .install-form,
  .upload-form {
    grid-template-columns: 1fr;
  }

  .install-card__head {
    flex-direction: column;
  }
}
</style>
