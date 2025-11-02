<template>
  <!-- 导航页：25 课卡片网格 -->
  <div class="nav">
    <NavBar />
    <div class="nav__header">
      <h1 class="nav__title">课程目录</h1>
    </div>
    <div class="nav__grid">
      <div v-for="i in 25" :key="i" class="card">
        <img
          v-if="thumb(i)"
          :src="thumb(i)"
          class="card__img"
          :alt="`lesson-${i}`"
        />
        <div v-else class="card__img--placeholder" :class="`hue-${i % 6}`"></div>
        <div class="card__body">
          <div class="card__no">第 {{ i }} 课</div>
          <h3 class="card__title">{{ title(i) }}</h3>
          <div class="card__tags">
            <span v-for="t in tags(i)" :key="t" class="tag">{{ t }}</span>
          </div>
          <router-link :to="`/slides/lesson-${String(i).padStart(2, '0')}`" class="card__btn">
            进入课程
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import NavBar from '../components/NavBar.vue'

interface LessonMeta {
  title: string
  slides: { type: string; content?: string; question?: string }[]
}

const lessons = ref<LessonMeta[]>([])

onMounted(async () => {
  // 预加载 25 课 json 取标题与知识点
  for (let i = 1; i <= 25; i++) {
    const res = await fetch(`${import.meta.env.BASE_URL}slides/lesson-${String(i).padStart(2, '0')}.json`)
    const json = (await res.json()) as LessonMeta
    lessons.value[i - 1] = json
  }
})

function title(idx: number): string {
  return lessons.value[idx - 1]?.title || `第 ${idx} 课`
}

function tags(idx: number): string[] {
  const k = lessons.value[idx - 1]?.slides
    ?.filter((s) => s.type === 'text' && s.content)
    .slice(0, 3)
    .map((s) => s.content!.replace(/[，。！？；：]/g, '').slice(0, 8)) || []
  return k.length ? k : ['气候变化', '数据探究', '行动方案']
}

function thumb(idx: number): string | null {
  // 优先 public/assets/images/lesson-xx-*.png
  try {
    const base = import.meta.env.BASE_URL
    // 伪映射：实际运行时可由构建脚本生成映射表，这里简化
    const map: Record<number, string> = {
      15: `${base}assets/images/lesson-15-evidence.png`,
      21: `${base}assets/images/lesson-21-co2-temp.png`,
    }
    return map[idx] || null
  } catch {
    return null
  }
}
</script>

<style scoped>
.nav {
  min-height: 100vh;
  background: #f5f7fa;
  font-family: "Heiti TC", "PingFang TC", sans-serif;
}
.nav__header {
  text-align: center;
  padding: 2rem 1rem 1rem;
}
.nav__title {
  font-size: 2rem;
  font-weight: 700;
  color: #00a79d;
  margin: 0;
}
.nav__grid {
  display: grid;
  gap: 1.5rem;
  padding: 1rem 2rem 3rem;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}
@media (min-width: 768px) {
  .nav__grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (min-width: 1024px) {
  .nav__grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}
.card__img {
  width: 100%;
  height: 140px;
  object-fit: cover;
  display: block;
}
.card__img--placeholder {
  width: 100%;
  height: 140px;
}
.hue-0 { background: linear-gradient(135deg, #ff6b35, #ff8c42); }
.hue-1 { background: linear-gradient(135deg, #00a79d, #00c9b1); }
.hue-2 { background: linear-gradient(135deg, #f9c80e, #fadc56); }
.hue-3 { background: linear-gradient(135deg, #5b85d9, #7ea5f6); }
.hue-4 { background: linear-gradient(135deg, #a463f2, #c797fa); }
.hue-5 { background: linear-gradient(135deg, #43e97b, #38f9d7); }

.card__body {
  padding: 1rem 1.25rem 1.5rem;
}
.card__no {
  font-size: 0.875rem;
  color: #999;
  margin-bottom: 0.25rem;
}
.card__title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 0.75rem;
  color: #333;
}
.card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.tag {
  display: inline-block;
  font-size: 0.75rem;
  background: #eef7f6;
  color: #00a79d;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}
.card__btn {
  display: inline-block;
  background: #ff6b35;
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.2s;
}
.card__btn:hover {
  background: #ff5722;
}
</style>