<template>
  <!-- 封面页：全屏居中 -->
  <div class="cover">
    <div class="cover__bg"></div>
    <div class="cover__content">
      <h1 class="cover__title">气候变化小卫士</h1>
      <p class="cover__subtitle">从数据到行动，解锁气候变化真相</p>
      <router-link to="/nav" class="cover__btn">开始学习</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
// 封面页组件
</script>

<style scoped>
.cover {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #fff;
  font-family: "Heiti TC", "PingFang TC", sans-serif;
}
.cover__bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #00a79d 0%, #006a61 100%);
  z-index: 0;
}
.cover__content {
  position: relative;
  z-index: 1;
  padding: 2rem;
}
.cover__title {
  font-size: 3rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
  letter-spacing: 0.05em;
}
.cover__subtitle {
  font-size: 1.25rem;
  margin: 0 0 2rem;
  opacity: 0.9;
}
.cover__btn {
  display: inline-block;
  background: #ff6b35;
  color: #fff;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  transition: transform 0.2s, background 0.2s;
}
.cover__btn:hover {
  background: #ff5722;
  transform: translateY(-2px);
}
@media (max-width: 640px) {
  .cover__title {
    font-size: 2.25rem;
  }
  .cover__subtitle {
    font-size: 1rem;
  }
}
</style>