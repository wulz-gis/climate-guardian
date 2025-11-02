/**
 * 气候小卫士课件入口
 * 读取 lesson-01.json → 生成 DOM → 初始化 Reveal
 */
import '../node_modules/reveal.js/dist/reveal.css'
import '../node_modules/reveal.js/dist/theme/white.css'
import '../node_modules/reveal.js/plugin/highlight/monokai.css'
import './style.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

createApp(App).use(router).mount('#app')