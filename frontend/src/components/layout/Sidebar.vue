<template>
  <div class="sidebar" :class="{ 'collapsed': isCollapsed }">
    <div class="sidebar-toggle" @click="toggleSidebar">
      <el-icon :class="isCollapsed ? 'el-icon-expand' : 'el-icon-collapse'">
        <ArrowRight v-if="isCollapsed" />
        <ArrowLeft v-else />
      </el-icon>
    </div>
    
    <div class="sidebar-content" v-if="!isCollapsed">
      <div class="sidebar-header">
        <h2>文件列表</h2>
      </div>
      
      <div class="sidebar-actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索文件..."
          prefix-icon="Search"
          clearable
          @input="searchFiles"
        />
        
        <el-button type="primary" @click="showUploadModal = true" class="upload-btn">
          <el-icon><Upload /></el-icon>
          <span>上传文件</span>
        </el-button>
      </div>
      
      <div class="file-list">
        <el-empty v-if="filteredFiles.length === 0" description="暂无文件" />
        <el-table
          v-else
          :data="filteredFiles"
          style="width: 100%"
          @row-click="handleRowClick"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column label="文件名">
            <template #default="scope">
              <div class="file-name">
                <el-icon><Document /></el-icon>
                <span>{{ scope.row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column width="50">
            <template #default="scope">
              <el-button
                type="danger"
                icon="Delete"
                circle
                size="small"
                @click.stop="deleteFile(scope.row.id)"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <div class="sidebar-footer">
        <el-button
          type="danger"
          :disabled="selectedFiles.length === 0"
          @click="batchDelete"
        >
          批量删除 ({{ selectedFiles.length }})
        </el-button>
      </div>
    </div>
    
    <!-- 上传模态框 -->
    <el-dialog
      v-model="showUploadModal"
      title="上传文件"
      width="30%"
    >
      <el-upload
        class="upload-demo"
        drag
        action="/api/documents/upload"
        multiple
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .docx, .pdf, .txt 等格式文件
          </div>
        </template>
      </el-upload>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showUploadModal = false">取消</el-button>
          <el-button type="primary" @click="showUploadModal = false">
            完成
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Document, 
  ArrowLeft, 
  ArrowRight, 
  Search, 
  Upload, 
  UploadFilled, 
  Delete 
} from '@element-plus/icons-vue'
import historyService from '../../services/history'

const router = useRouter()
const emit = defineEmits(['collapse-change'])

// 侧边栏状态
const isCollapsed = ref(false)
const searchQuery = ref('')
const showUploadModal = ref(false)
const selectedFiles = ref([])
const activeFileId = ref(null)

// 监听折叠状态变化并发射事件
watch(isCollapsed, (newValue) => {
  emit('collapse-change', newValue)
})

// 模拟文件数据
const files = ref([
  { id: 1, name: '结构分析报告.docx', type: 'docx', size: '1.2MB', uploadTime: '2023-05-15 10:30:00' },
  { id: 2, name: '测试结果汇总.pdf', type: 'pdf', size: '3.5MB', uploadTime: '2023-05-14 15:45:00' },
  { id: 3, name: '项目计划书.docx', type: 'docx', size: '0.8MB', uploadTime: '2023-05-13 09:20:00' }
])

// 过滤后的文件列表
const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value
  
  return files.value.filter(file => 
    file.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// 切换侧边栏
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

// 搜索文件
const searchFiles = () => {
  // 实际应用中可能需要调用API进行搜索
}

// 选择文件
const handleRowClick = (row) => {
  activeFileId.value = row.id
  router.push(`/tree-view/${row.id}`)
  
  // 添加操作记录
  historyService.addOperation({
    description: `查看文件：${row.name}`,
    type: 'info'
  })
}

// 删除文件
const deleteFile = (id) => {
  ElMessageBox.confirm(
    '确定要删除此文件吗？此操作不可恢复。',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(() => {
      // 实际应用中应该调用API删除文件
      files.value = files.value.filter(file => file.id !== id)
      
      // 添加操作记录
      historyService.addOperation({
        description: `删除文件：${files.value.find(f => f.id === id)?.name || 'unknown'}`,
        type: 'danger'
      })
      
      ElMessage.success('文件已删除')
    })
    .catch(() => {
      // 用户取消操作，不做处理
    })
}

// 批量删除
const batchDelete = () => {
  if (selectedFiles.value.length === 0) return
  
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedFiles.value.length} 个文件吗？此操作不可恢复。`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(() => {
      // 实际应用中应该调用API批量删除文件
      files.value = files.value.filter(file => !selectedFiles.value.includes(file.id))
      selectedFiles.value = []
      
      // 添加操作记录
      historyService.addOperation({
        description: `批量删除了 ${selectedFiles.value.length} 个文件`,
        type: 'danger'
      })
      
      ElMessage.success('文件已删除')
    })
    .catch(() => {
      // 用户取消操作，不做处理
    })
}

// 上传成功
const handleUploadSuccess = (response, file) => {
  ElMessage.success(`文件 ${file.name} 上传成功`)
  
  // 添加到文件列表
  files.value.unshift({
    id: Date.now(),
    name: file.name,
    type: file.name.split('.').pop(),
    size: (file.size / 1024 / 1024).toFixed(2) + 'MB',
    uploadTime: new Date().toLocaleString()
  })
  
  // 添加操作记录
  historyService.addOperation({
    description: `上传文件：${file.name}`,
    type: 'success'
  })
}

// 上传失败
const handleUploadError = (err, file) => {
  ElMessage.error(`文件 ${file.name} 上传失败`)
}
</script>

<style scoped>
.sidebar {
  width: 300px;
  height: 100vh;
  background-color: #fff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  transition: width 0.3s;
  position: fixed;
  top: 60px; /* 导航栏高度 */
  left: 0;
  bottom: 0;
  overflow-y: auto;
  z-index: 900;
}

.sidebar.collapsed {
  width: 30px;
}

.sidebar-toggle {
  position: absolute;
  top: 20px;
  right: 10px;
  width: 20px;
  height: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  z-index: 10;
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.sidebar-header {
  margin-bottom: 20px;
}

.sidebar-header h2 {
  font-size: 18px;
  color: #303133;
  margin: 0;
}

.sidebar-actions {
  margin-bottom: 20px;
}

.upload-btn {
  margin-top: 10px;
  width: 100%;
}

.file-list {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 20px;
}

.file-name {
  display: flex;
  align-items: center;
}

.file-name .el-icon {
  margin-right: 5px;
  color: #409EFF;
}

.sidebar-footer {
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}
</style> 