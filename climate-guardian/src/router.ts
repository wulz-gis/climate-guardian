import { createRouter, createWebHistory } from 'vue-router'
import Cover from './pages/Cover.vue'
import Nav from './pages/Nav.vue'

const routes = [
  { path: '/', name: 'Cover', component: Cover },
  { path: '/nav', name: 'Nav', component: Nav },
  // 保持原有幻灯片路由不变（动态导入减少首屏体积）；props:true 以将 :id 作为组件属性传递
  { path: '/slides/:id', name: 'Slides', component: () => import('./slides/RevealSlides.vue'), props: true },
  // 旧根路径重定向到导航页
  { path: '/index.html', redirect: '/nav' }
]

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})