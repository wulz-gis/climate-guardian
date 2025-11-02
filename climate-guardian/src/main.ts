/**
 * 气候小卫士课件入口
 * 读取 lesson-01.json → 生成 DOM → 初始化 Reveal
 */
import '../node_modules/reveal.js/dist/reveal.css'
import '../node_modules/reveal.js/dist/theme/white.css'
import '../node_modules/reveal.js/plugin/highlight/monokai.css'
import './style.css'

import { defaultConfig, buildSlides } from './utils/reveal'
import { renderChart } from './components/ChartRenderer'

/**
 * 启动应用：加载幻灯片 JSON，渲染 DOM，并初始化 Reveal 与图表。
 * - 使用 import.meta.env.BASE_URL 保证在 GitHub Pages 子路径下能正确解析资源。
 * - 通过 window.location.origin 拼接为绝对 URL，避免在开发环境中构造无效基地址。
 */
async function bootstrap(): Promise<void> {
  // 构造绝对基地址（如 http://localhost:5175/climate-guardian/ 或 https://wulz-gis.github.io/climate-guardian/）
  const absoluteBase = new URL(import.meta.env.BASE_URL, window.location.origin)
  // 从 public/slides 读取课件 JSON
  const slidesUrl = new URL('slides/lesson-01.json', absoluteBase).toString()
  const res = await fetch(slidesUrl)
  const json = await res.json()

  // 注入幻灯片 DOM
  document.querySelector<HTMLDivElement>('.slides')!.innerHTML = buildSlides(json)

  // 初始化 Reveal
  const Reveal = (await import('reveal.js')).default
  Reveal.initialize(defaultConfig)

  // 按需渲染图表
  document.querySelectorAll('section.chart').forEach((sec) => {
    const type = sec.getAttribute('data-chart-type')!
    const src = sec.getAttribute('data-src')!
    const chartDiv = sec.querySelector<HTMLElement>('div[id^="chart"]')!
    renderChart(chartDiv, type, src)
  })
}

bootstrap()