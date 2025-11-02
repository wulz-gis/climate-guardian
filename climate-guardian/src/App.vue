<template>
  <!-- 应用根组件：承载路由视图 -->
  <router-view />
</template>

<script setup lang="ts">
/**
 * 应用根组件
 *
 * 负责挂载路由视图。页面级组件（封面、目录、幻灯片）通过路由切换呈现。
 */
</script>

<style>
/* 全局基础字体（macOS 使用 Heiti TC） */
:root {
  font-family: "Heiti TC", "PingFang TC", -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  color: #111;
}
html, body, #app {
  height: 100%;
  margin: 0;
}
</style>