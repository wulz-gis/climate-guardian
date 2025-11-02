<template>
  <!-- 全局顶部导航栏 -->
  <header class="navbar">
    <div class="navbar__left">
      <router-link to="/" class="navbar__brand">气候小卫士</router-link>
    </div>
    <div class="navbar__right">
      <router-link to="/nav" class="navbar__link">目录</router-link>
    </div>
  </header>
</template>

<script setup lang="ts">
// 全局导航栏组件
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
.navbar__brand {
  font-size: 1.25rem;
  font-weight: 700;
  color: #00a79d;
  text-decoration: none;
  letter-spacing: 0.05em;
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
.navbar__link:hover {
  background: #f3f4f6;
}
</style>