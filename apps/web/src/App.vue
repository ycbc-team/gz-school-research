<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';
</script>

<template>
  <header class="app-header">
    <RouterLink to="/" class="brand">广州学校升学调研</RouterLink>
    <nav class="app-nav">
      <RouterLink to="/map">地图</RouterLink>
      <RouterLink to="/linkage">升学路径</RouterLink>
      <RouterLink to="/support">支撑度</RouterLink>
      <RouterLink to="/policy">政策说明</RouterLink>
    </nav>
  </header>
  <main class="app-main">
    <RouterView v-slot="{ Component }">
      <!-- keep-alive：地图等页面在进入详情页后不销毁，返回时原路恢复筛选/视图状态 -->
      <KeepAlive>
        <component :is="Component" />
      </KeepAlive>
    </RouterView>
  </main>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e3dd;
  position: sticky;
  top: 0;
  z-index: 1000;
}
.brand {
  font-size: 16px;
  font-weight: 700;
  color: #1a1b1c;
  text-decoration: none;
}
.app-nav {
  display: flex;
  gap: 16px;
}
.app-nav a {
  font-size: 14px;
  color: #6b7280;
  text-decoration: none;
  padding: 4px 2px;
}
.app-nav a.router-link-active {
  color: #3a5396;
  font-weight: 600;
  border-bottom: 2px solid #9bbbf4;
}
.app-main {
  max-width: 1080px;
  margin: 0 auto;
  padding: 20px 16px 48px;
}
</style>
