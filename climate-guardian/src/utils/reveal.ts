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
 *
 * - 兼容不同字段命名（如 bullets/objectives, video/videoSrc 等）
 * - 对缺失字段进行安全回退，避免页面出现“undefined”
 * - 兼容旧版模式：支持 type="title" 与 type="text"，识别 content/data/question
 */
export function buildSlides(json: any): string {
  return json.slides
    .map((s: any) => {
      switch (s.type) {
        case 'cover': {
          const title = s.title ?? ''
          const subtitle = s.subtitle ?? ''
          return `
            <section class="cover">
              <h1 class="text-5xl font-bold">${title}</h1>
              ${subtitle ? `<p class="text-2xl mt-4 text-gray-600">${subtitle}</p>` : ''}
            </section>`
        }
        case 'objective': {
          const items: string[] = (s.bullets ?? s.objectives ?? []) as string[]
          return `
            <section class="objective">
              <h2>${s.title ?? ''}</h2>
              ${Array.isArray(items) && items.length ? `<ul class="text-xl mt-6 space-y-3">
                ${items.map((b: string) => `<li>${b}</li>`).join('')}
              </ul>` : ''}
            </section>`
        }
        case 'video': {
          const videoSrc = s.video ?? s.videoSrc ?? ''
          const placeholder = s.placeholder ?? s.coverImage ?? ''
          const qs: string[] = (s.questions ?? s.question ?? []) as string[]
          return `
            <section class="video" ${placeholder ? `data-background-image="${placeholder}"` : ''}>
              <h2>${s.title ?? ''}</h2>
              ${videoSrc ? `<video class="w-3/4 mx-auto" controls src="${videoSrc}"></video>` : ''}
              ${Array.isArray(qs) && qs.length ? `<p class="mt-4 text-lg">${qs.join(' ')}</p>` : ''}
            </section>`
        }
        case 'concept': {
          const content = s.content ?? ''
          return `
            <section class="concept">
              <h2>${s.title ?? ''}</h2>
              ${content ? `<p class="text-2xl mt-6">${content}</p>` : ''}
            </section>`
        }
        case 'chart': {
          const chartType = s.chartType ?? s.type ?? 'line'
          const dataSrc = s.dataSrc ?? s.src ?? s.data ?? ''
          const idAttr = String(s.title ?? 'chart').replace(/\s+/g, '-')
          return `
            <section class="chart" data-chart-type="${chartType}" data-src="${dataSrc}">
              <h2>${s.title ?? ''}</h2>
              <div id="chart-${idAttr}" class="w-full h-[420px]"></div>
            </section>`
        }
        case 'interaction': {
          const task = s.task ?? s.content ?? ''
          return `
            <section class="interaction">
              <h2>${s.title ?? ''}</h2>
              ${task ? `<p class="text-xl">${task}</p>` : ''}
              <div id="interaction-area" class="mt-6"></div>
            </section>`
        }
        case 'discussion': {
          const questions: string[] = (s.questions ?? s.question ?? []) as string[]
          return `
            <section class="discussion">
              <h2>${s.title ?? ''}</h2>
              ${Array.isArray(questions) && questions.length ? `<ul class="text-xl mt-6 space-y-3">
                ${questions.map((q: string) => `<li>• ${q}</li>`).join('')}
              </ul>` : ''}
            </section>`
        }
        case 'summary': {
          const bullets: string[] = (s.bullets ?? s.points ?? []) as string[]
          return `
            <section class="summary">
              <h2>${s.title ?? ''}</h2>
              ${Array.isArray(bullets) && bullets.length ? `<ul class="text-xl mt-6 space-y-3">
                ${bullets.map((b: string) => `<li>${b}</li>`).join('')}
              </ul>` : ''}
            </section>`
        }
        // 兼容旧版：标题页
        case 'title': {
          const content = s.content ?? s.title ?? ''
          return `
            <section class="cover">
              <h1 class="text-5xl font-bold">${content}</h1>
            </section>`
        }
        // 兼容旧版：文本页（学习目标/思考题/普通文本）
        case 'text': {
          const heading = s.content ?? s.title ?? ''
          const dataList: string[] = (s.data ?? []) as string[]
          const qList: string[] = (s.question ?? s.questions ?? []) as string[]
          const body = s.body ?? s.description ?? ''
          // 动态选择呈现：优先列表项，其次问题列表，否则正文
          const listHtml = Array.isArray(dataList) && dataList.length
            ? `<ul class="text-xl mt-6 space-y-3">${dataList.map((d: string) => `<li>${d}</li>`).join('')}</ul>`
            : ''
          const qHtml = Array.isArray(qList) && qList.length
            ? `<ul class="text-xl mt-6 space-y-3">${qList.map((d: string) => `<li>• ${d}</li>`).join('')}</ul>`
            : ''
          const bodyHtml = body ? `<p class="text-2xl mt-6">${body}</p>` : ''
          return `
            <section class="concept">
              <h2>${heading}</h2>
              ${listHtml || qHtml || bodyHtml}
            </section>`
        }
        default:
          return `<section>${s.title ?? s.content ?? ''}</section>`
      }
    })
    .join('')
}