<template>
  <div class="navbar">
    <div class="navbar-container">
      <!-- Logo区域 - 最左边 -->
      <div class="logo-container" @click="goToHome">
        <el-icon class="logo-icon"><Document /></el-icon>
        <h1 class="logo-text">文档关键信息提取系统</h1>
      </div>
      
      <!-- 导航链接区域 - 中间 -->
      <div class="nav-links">
        <router-link to="/tree-view" class="nav-link" :class="{ 'active': isActive('/tree-view') }">
          <el-icon><Connection /></el-icon>
          <span>提取结果树状图</span>
        </router-link>
      </div>
      
      <!-- 操作记录 - 最右边 -->
      <div class="history-btn">
        <div class="nav-link" @click="showHistoryDialog = true">
          <el-icon><Timer /></el-icon>
          <span>操作记录</span>
        </div>
      </div>
    </div>
    
    <!-- 操作记录弹窗 -->
    <el-dialog
      v-model="showHistoryDialog"
      title="操作记录"
      width="50%"
      :before-close="handleCloseDialog"
    >
      <div class="history-list">
        <el-empty v-if="operationHistory.length === 0" description="暂无操作记录" />
        <el-timeline v-else>
          <el-timeline-item
            v-for="(item, index) in operationHistory"
            :key="index"
            :timestamp="item.timestamp"
            :type="item.type"
          >
            {{ item.description }}
            <div class="operation-actions">
              <el-button 
                v-if="!item.undone" 
                type="danger" 
                size="small" 
                @click="undoOperation(item.id)"
              >
                撤销
              </el-button>
              <el-button 
                v-else 
                type="primary" 
                size="small" 
                @click="redoOperation(item.id)"
              >
                重做
              </el-button>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showHistoryDialog = false">关闭</el-button>
          <el-button type="danger" @click="clearHistory" :disabled="operationHistory.length === 0">
            清空记录
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Document, Connection, Timer } from '@element-plus/icons-vue'
import historyService from '../../services/history'

const route = useRoute()
const router = useRouter()

// 检查路由是否激活
const isActive = (path) => {
  return route.path.startsWith(path)
}

// 跳转到首页
const goToHome = () => {
  router.push('/')
}

// 操作记录相关
const showHistoryDialog = ref(false)
const operationHistory = computed(() => historyService.getHistory())

// 关闭弹窗
const handleCloseDialog = () => {
  showHistoryDialog.value = false
}

// 撤销操作
const undoOperation = (id) => {
  if (historyService.undoOperation(id)) {
    // 实际应用中这里应该调用API进行撤销操作
  }
}

// 重做操作
const redoOperation = (id) => {
  if (historyService.redoOperation(id)) {
    // 实际应用中这里应该调用API进行重做操作
  }
}

// 清空历史记录
const clearHistory = () => {
  ElMessageBox.confirm(
    '确定要清空所有操作记录吗？此操作不可恢复。',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(() => {
      historyService.clearHistory()
    })
    .catch(() => {
      // 用户取消操作，不做处理
    })
}
</script>

<style scoped>
.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background-color: #545c64;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.navbar-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
  max-width: 1200px;
  margin: 0 auto;
}

.logo-container {
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: opacity 0.3s;
}

.logo-container:hover {
  opacity: 0.8;
}

.logo-icon {
  font-size: 24px;
  color: #ffd04b;
  margin-right: 10px;
}

.logo-text {
  color: #fff;
  font-size: 18px;
  margin: 0;
}

.nav-links {
  display: flex;
  justify-content: center;
  flex: 1;
}

.nav-link {
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  color: #fff;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s;
}

.nav-link:hover, .nav-link.active {
  color: #ffd04b;
  background-color: #434a50;
}

.nav-link .el-icon {
  margin-right: 5px;
}

.history-btn {
  display: flex;
  align-items: center;
}

.history-list {
  max-height: 400px;
  overflow-y: auto;
}

.operation-actions {
  margin-top: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
}
</style> 