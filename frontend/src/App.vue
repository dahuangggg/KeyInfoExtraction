<template>
  <div class="app">
    <Navbar />
    <div class="content-container">
      <Sidebar v-if="showSidebar" ref="sidebar" @collapse-change="handleSidebarCollapse" />
      <main class="main-content" :class="{ 'with-sidebar': showSidebar && !isSidebarCollapsed, 'with-collapsed-sidebar': showSidebar && isSidebarCollapsed }">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from './components/layout/Navbar.vue'
import Sidebar from './components/layout/Sidebar.vue'

const route = useRoute()
const isSidebarCollapsed = ref(false)

// 根据路由决定是否显示侧边栏
const showSidebar = computed(() => {
  // 在某些页面不显示侧边栏，例如首页
  return route.path !== '/'
})

// 处理侧边栏折叠状态变化
const handleSidebarCollapse = (collapsed) => {
  isSidebarCollapsed.value = collapsed
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f5f7fa;
  color: #303133;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.content-container {
  display: flex;
  flex: 1;
  margin-top: 60px; /* 导航栏高度 */
}

.main-content {
  flex: 1;
  padding: 20px;
  transition: margin-left 0.3s;
}

.main-content.with-sidebar {
  margin-left: 300px; /* 侧边栏宽度 */
}

.main-content.with-collapsed-sidebar {
  margin-left: 30px; /* 折叠后的侧边栏宽度 */
}
</style> 