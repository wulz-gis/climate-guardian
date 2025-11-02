<template>
  <div class="slides-container">
    <NavBar />
    <div class="reveal">
      <div class="slides"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import NavBar from '../components/NavBar.vue'
import { defaultConfig, buildSlides } from '../utils/reveal'
import { renderChart } from '../components/ChartRenderer'

const props = defineProps<{ id: string }>()

onMounted(async () => {
  const absoluteBase = new URL(import.meta.env.BASE_URL, window.location.origin)
  const slidesUrl = new URL(`slides/${props.id}.json`, absoluteBase).toString()
  const res = await fetch(slidesUrl)
  const json = await res.json()

  document.querySelector<HTMLDivElement>('.slides')!.innerHTML = buildSlides(json)

  const Reveal = (await import('reveal.js')).default
  Reveal.initialize(defaultConfig)

  document.querySelectorAll('section.chart').forEach((sec) => {
    const type = sec.getAttribute('data-chart-type')!
    const src = sec.getAttribute('data-src')!
    const chartDiv = sec.querySelector<HTMLElement>('div[id^="chart"]')!
    renderChart(chartDiv, type, src)
  })
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