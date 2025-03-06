import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import TreeView from '../views/TreeView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: {
      title: '文档关键信息提取'
    }
  },
  {
    path: '/tree-view',
    name: 'TreeView',
    component: TreeView,
    meta: {
      title: '提取结果树状图'
    }
  },
  {
    path: '/tree-view/:id',
    name: 'TreeViewDetail',
    component: TreeView,
    meta: {
      title: '提取结果树状图详情'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫，设置页面标题
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || '文档关键信息提取系统'
  next()
})

export default router 