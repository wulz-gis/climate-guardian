<template>
  <!-- 全局顶部导航栏 -->
  <header class="navbar" :class="{ compact }">
    <div class="navbar__left">
      <router-link to="/" class="navbar__brand">气候小卫士</router-link>
    </div>
    <div class="navbar__right">
      <router-link to="/nav" class="navbar__link">目录</router-link>
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * 导航栏组件（支持紧凑模式）
 *
 * Props:
 * - compact: 是否使用紧凑样式，减少高度与内边距
 */
const props = withDefaults(defineProps<{ compact?: boolean }>(), {
  compact: false,
})

const compact = props.compact
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 2rem;
  background: #ffffffee;
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 100;
  font-family: "Heiti TC", "PingFang TC", sans-serif;
}
.navbar.compact {
  height: 44px;
  padding: 0 1rem;
}
.navbar__brand {
  font-size: 1.25rem;
  font-weight: 700;
  color: #00a79d;
  text-decoration: none;
  letter-spacing: 0.05em;
}
.navbar.compact .navbar__brand {
  font-size: 1rem;
}
.navbar__link {
  font-size: 1rem;
  font-weight: 600;
  color: #333;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  transition: background 0.2s;
}
.navbar.compact .navbar__link {
  font-size: 0.875rem;
  padding: 0.25rem 0.75rem;
}
.navbar__link:hover {
  background: #f3f4f6;
}
</style>