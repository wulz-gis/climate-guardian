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

async function bootstrap(): Promise<void> {
  const res = await fetch('/src/slides/lesson-01.json')
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