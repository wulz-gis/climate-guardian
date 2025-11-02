/**
 * Reveal 基础配置与初始化
 * 默认主题、插件、字体均按课件指南设置
 */
import Reveal from 'reveal.js'
import RevealHighlight from 'reveal.js/plugin/highlight/highlight'
import RevealNotes from 'reveal.js/plugin/notes/notes'

export function initReveal(container: HTMLElement): Reveal.Api {
  const reveal = new Reveal(container, {
    plugins: [RevealHighlight, RevealNotes],
    hash: true,
    controls: true,
    progress: true,
    center: true,
    transition: 'slide'
  })
  reveal.initialize()
  return reveal
}

export const defaultConfig: Reveal.Options = {
  hash: true,
  controls: true,
  progress: true,
  center: true,
  transition: 'slide',
  backgroundTransition: 'fade',
  plugins: [RevealHighlight, RevealNotes],
  // 课件指南：16:9 投影，字号 24+，行高 1.4

  width: 1280,
  height: 720,
  margin: 0.08,
  minScale: 0.5,
  maxScale: 2
}

/**
 * 根据 JSON 配置生成幻灯片 DOM
 */
export function buildSlides(json: any): string {
  return json.slides
    .map((s: any) => {
      switch (s.type) {
        case 'cover':
          return `
            <section class="cover">
              <h1 class="text-5xl font-bold">${s.title}</h1>
              <p class="text-2xl mt-4 text-gray-600">${s.subtitle}</p>
            </section>`
        case 'objective':
          return `
            <section class="objective">
              <h2>${s.title}</h2>
              <ul class="text-xl mt-6 space-y-3">
                ${s.bullets.map((b: string) => `<li>${b}</li>`).join('')}
              </ul>
            </section>`
        case 'video':
          return `
            <section class="video" data-background-image="${s.placeholder}">
              <h2>${s.title}</h2>
              <video class="w-3/4 mx-auto" controls src="${s.video}"></video>
              <p class="mt-4 text-lg">${s.questions?.join(' ')}</p>
            </section>`
        case 'concept':
          return `
            <section class="concept">
              <h2>${s.title}</h2>
              <p class="text-2xl mt-6">${s.content}</p>
            </section>`
        case 'chart':
          return `
            <section class="chart" data-chart-type="${s.chartType}" data-src="${s.dataSrc}">
              <h2>${s.title}</h2>
              <div id="chart-${s.title}" class="w-full h-[420px]"></div>
            </section>`
        case 'interaction':
          return `
            <section class="interaction">
              <h2>${s.title}</h2>
              <p class="text-xl">${s.task}</p>
              <div id="interaction-area" class="mt-6"></div>
            </section>`
        case 'discussion':
          return `
            <section class="discussion">
              <h2>${s.title}</h2>
              <ul class="text-xl mt-6 space-y-3">
                ${s.questions.map((q: string) => `<li>• ${q}</li>`).join('')}
              </ul>
            </section>`
        case 'summary':
          return `
            <section class="summary">
              <h2>${s.title}</h2>
              <ul class="text-xl mt-6 space-y-3">
                ${s.bullets.map((b: string) => `<li>${b}</li>`).join('')}
              </ul>
            </section>`
        default:
          return `<section>${s.title}</section>`
      }
    })
    .join('')
}