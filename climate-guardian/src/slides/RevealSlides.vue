<template>
  <div class="slides-container">
    <NavBar :compact="true" />
    <div class="reveal">
      <div class="slides"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 幻灯片页面容器
 *
 * - 启用紧凑导航栏以减少头部空间占用
 * - 根据路由参数 id 加载对应 lesson-xx.json；当 id 变化时重新加载
 * - 在切换课程或卸载组件时正确销毁 Reveal 实例，避免重复初始化
 */
import { onMounted, onUnmounted, watch } from 'vue'
import NavBar from '../components/NavBar.vue'
import { defaultConfig, buildSlides, initReveal } from '../utils/reveal'
import { renderChart } from '../components/ChartRenderer'

const props = defineProps<{ id: string }>()

// 当前 Reveal 实例句柄，用于在切换课程或卸载时销毁
let deck: any | null = null

// 本地 JSON 课程文件映射（兼容开发环境与未复制到 public 的情况）
const localSlides = import.meta.glob('./lesson-*.json', { eager: true }) as Record<string, any>

function destroyReveal(): void {
  /**
   * 销毁当前 Reveal 实例以释放事件监听与状态。
   * 在课程切换前和组件卸载时调用，防止“已初始化”错误。
   */
  try {
    deck?.destroy()
  } catch (e) {
    // 忽略销毁时的异常，确保流程继续进行
    console.warn('[Reveal] destroy failed:', e)
  } finally {
    deck = null
  }
}

async function loadSlides(id: string): Promise<void> {
  /**
   * 加载并渲染指定课程的幻灯片。
   *
   * Args:
   *   id: 课程ID（如 'lesson-02'）。
   */
  // 切换课程前先销毁旧实例，避免重复初始化
  destroyReveal()

  const absoluteBase = new URL(import.meta.env.BASE_URL, window.location.origin)
  const slidesUrl = new URL(`slides/${id}.json`, absoluteBase).toString()

  let json: any | null = null

  try {
    const res = await fetch(slidesUrl)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    json = await res.json()
  } catch (fetchErr) {
    // 回退：尝试从本地打包的 JSON 模块加载
    const key = `./${id}.json`
    const mod = localSlides[key]
    json = mod?.default ?? mod ?? null
    if (!json) {
      console.error('[Reveal] fetch failed & local fallback missing:', fetchErr)
    } else {
      console.warn('[Reveal] using local JSON fallback for', id)
    }
  }

  try {
    const slidesEl = document.querySelector<HTMLDivElement>('.slides')
    if (!slidesEl) throw new Error('Missing .slides container')

    if (json) {
      // 重新渲染 slides 容器内容
      slidesEl.innerHTML = buildSlides(json)
    } else {
      // 友好错误提示与回退内容
      slidesEl.innerHTML = `
        <section class="error">
          <h2>课件数据加载失败</h2>
          <p>无法加载 ${id}.json。请检查网络或文件是否存在。</p>
          <p><a href="${import.meta.env.BASE_URL}nav">返回目录</a></p>
        </section>`
    }

    // 初始化 Reveal 实例（使用容器实例化而非单例）
    const revealEl = document.querySelector<HTMLElement>('.reveal')!
    deck = initReveal(revealEl)

    // 渲染所有图表
    document.querySelectorAll('section.chart').forEach((sec) => {
      const type = sec.getAttribute('data-chart-type')!
      const src = sec.getAttribute('data-src')!
      const chartDiv = sec.querySelector<HTMLElement>('div[id^="chart"]')!
      renderChart(chartDiv, type, src)
    })
  } catch (err) {
    console.error('[Reveal] loadSlides render/init error:', err)
    // 保底：若渲染或初始化仍出错，提示用户返回目录
    const slidesEl = document.querySelector<HTMLDivElement>('.slides')
    if (slidesEl) {
      slidesEl.innerHTML = `
        <section class="error">
          <h2>课件渲染失败</h2>
          <p>抱歉，页面暂时无法正常显示。请返回目录重试。</p>
          <p><a href="${import.meta.env.BASE_URL}nav">返回目录</a></p>
        </section>`
    }
  }
}

onMounted(() => {
  loadSlides(props.id)
})

watch(
  () => props.id,
  (newId) => {
    loadSlides(newId)
  }
)

onUnmounted(() => {
  /**
   * 组件卸载时清理 Reveal 实例，避免遗留监听与重复初始化。
   */
  destroyReveal()
})
</script>

<style scoped>
.slides-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.reveal {
  flex: 1;
}
</style>