<template>
  <div class="tree-view-container">
    <el-row :gutter="20" class="tree-view-content">
      <!-- 左侧树状结构 -->
      <el-col :span="8" class="tree-panel">
        <el-card class="tree-card">
          <template #header>
            <div class="card-header">
              <h3>提取结果树状结构</h3>
              <div class="header-actions">
                <el-button type="primary" size="small" @click="expandAll">
                  <el-icon><full-screen /></el-icon>
                  全部展开
                </el-button>
                <el-button type="info" size="small" @click="collapseAll">
                  <el-icon><aim /></el-icon>
                  全部折叠
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="tree-container">
            <el-tree
              ref="treeRef"
              :data="treeData"
              :props="defaultProps"
              node-key="id"
              highlight-current
              :expand-on-click-node="false"
              @node-click="handleNodeClick"
            >
              <template #default="{ node, data }">
                <span class="custom-tree-node">
                  <span>{{ node.label }}</span>
                  <span v-if="data.value" class="node-value">: {{ data.value }}</span>
                </span>
              </template>
            </el-tree>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧文档内容 -->
      <el-col :span="16" class="document-panel">
        <el-card class="document-card">
          <template #header>
            <div class="card-header">
              <h3>原文档内容</h3>
              <div class="header-actions">
                <el-button type="success" size="small" @click="downloadOriginalDoc">
                  <el-icon><download /></el-icon>
                  下载原文档
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="document-container">
            <div v-if="selectedNode" class="highlight-info">
              <el-alert
                title="已选中节点对应的原文内容"
                type="info"
                :closable="false"
                show-icon
              >
                <template #default>
                  <div class="selected-path">
                    路径: <span class="path-text">{{ getNodePath(selectedNode) }}</span>
                  </div>
                </template>
              </el-alert>
            </div>
            
            <div class="document-content" v-html="documentContent"></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FullScreen, Aim, Download } from '@element-plus/icons-vue'
import { getDocumentDetail } from '../api/document'
import historyService from '../services/history'

const route = useRoute()
const treeRef = ref(null)
const documentData = ref(null)
const selectedNode = ref(null)
const isLoading = ref(false)

// 树配置
const defaultProps = {
  children: 'children',
  label: 'label'
}

// 模拟数据 - 实际应用中应从API获取
const treeData = ref([
  {
    id: 1,
    label: '基本信息',
    children: [
      { id: 11, label: '文档标题', value: '结构分析报告' },
      { id: 12, label: '文档编号', value: 'CA15110' },
      { id: 13, label: '创建日期', value: '2023-05-15' }
    ]
  },
  {
    id: 2,
    label: '结构参数',
    children: [
      { id: 21, label: '材料', value: '铝合金' },
      { 
        id: 22, 
        label: '尺寸', 
        children: [
          { id: 221, label: '长度', value: '120mm' },
          { id: 222, label: '宽度', value: '80mm' },
          { id: 223, label: '高度', value: '25mm' }
        ]
      },
      { id: 23, label: '重量', value: '350g' }
    ]
  },
  {
    id: 3,
    label: '测试结果',
    children: [
      { id: 31, label: '强度测试', value: '通过' },
      { id: 32, label: '疲劳测试', value: '通过' },
      { id: 33, label: '温度测试', value: '部分通过' }
    ]
  }
])

// 模拟文档内容 - 实际应用中应从API获取
const documentContent = ref(`
  <h1 style="text-align: center;">结构分析报告</h1>
  <p style="text-align: right;">文档编号: CA15110</p>
  <p style="text-align: right;">创建日期: 2023-05-15</p>
  
  <h2>1. 概述</h2>
  <p>本报告详细分析了铝合金结构件的各项参数和测试结果。</p>
  
  <h2>2. 结构参数</h2>
  <h3>2.1 材料</h3>
  <p>本结构件采用高强度铝合金材料制造，具有重量轻、强度高的特点。</p>
  
  <h3>2.2 尺寸</h3>
  <p>结构件的主要尺寸如下：</p>
  <ul>
    <li>长度: 120mm</li>
    <li>宽度: 80mm</li>
    <li>高度: 25mm</li>
  </ul>
  
  <h3>2.3 重量</h3>
  <p>结构件总重量为350g，符合设计要求。</p>
  
  <h2>3. 测试结果</h2>
  <h3>3.1 强度测试</h3>
  <p>在标准负载下，结构件未出现变形或断裂，测试结果为<strong>通过</strong>。</p>
  
  <h3>3.2 疲劳测试</h3>
  <p>经过10,000次循环负载测试，结构件未出现裂纹或性能下降，测试结果为<strong>通过</strong>。</p>
  
  <h3>3.3 温度测试</h3>
  <p>在-40°C至85°C温度范围内，结构件基本保持稳定性能，但在高温环境下有轻微变形，测试结果为<strong>部分通过</strong>。</p>
  
  <h2>4. 结论</h2>
  <p>该结构件总体性能良好，满足大部分使用场景需求，建议在高温环境下谨慎使用。</p>
`)

// 获取文档数据
const fetchDocumentData = async () => {
  const documentId = route.params.id
  if (!documentId) return
  
  isLoading.value = true
  try {
    const response = await getDocumentDetail(documentId)
    documentData.value = response.data
    
    // 更新树数据和文档内容
    if (documentData.value) {
      // 实际应用中应处理API返回的数据
      // treeData.value = convertToTreeData(documentData.value.extractedInfo)
      // documentContent.value = documentData.value.originalText
    }
  } catch (error) {
    ElMessage.error('获取文档数据失败')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

// 处理节点点击
const handleNodeClick = (data) => {
  selectedNode.value = data
  
  // 添加操作记录
  addOperationHistory({
    description: `查看节点：${data.label}${data.value ? ' - ' + data.value : ''}`,
    type: 'info'
  })
  
  // 在实际应用中，这里可以高亮显示文档中对应的内容
  // 或者滚动到文档中对应的位置
}

// 获取节点路径
const getNodePath = (node) => {
  if (!node) return ''
  
  // 这里简化处理，实际应用中应该递归查找完整路径
  return `${node.label}${node.value ? ': ' + node.value : ''}`
}

// 展开所有节点
const expandAll = () => {
  // 使用更简单的方法，直接设置默认展开所有
  if (treeRef.value) {
    try {
      // 尝试使用Element Plus提供的方法
      const nodes = treeRef.value.store.nodesMap
      Object.keys(nodes).forEach(key => {
        nodes[key].expanded = true
      })
    } catch (error) {
      console.error('展开所有节点失败:', error)
      // 备用方案：重新渲染树
      const currentData = [...treeData.value]
      treeData.value = []
      setTimeout(() => {
        treeData.value = currentData
      }, 10)
    }
  }
}

// 折叠所有节点
const collapseAll = () => {
  // 使用更简单的方法
  if (treeRef.value) {
    try {
      // 尝试使用Element Plus提供的方法
      const nodes = treeRef.value.store.nodesMap
      Object.keys(nodes).forEach(key => {
        nodes[key].expanded = false
      })
    } catch (error) {
      console.error('折叠所有节点失败:', error)
    }
  }
}

// 下载原文档
const downloadOriginalDoc = () => {
  // 实际应用中应该调用API下载原文档
  ElMessage.success('开始下载原文档')
  
  // 添加操作记录
  addOperationHistory({
    description: '下载原文档',
    type: 'success'
  })
}

// 添加操作记录
const addOperationHistory = (operation) => {
  historyService.addOperation(operation)
}

onMounted(() => {
  fetchDocumentData()
})
</script>

<style scoped>
.tree-view-container {
  padding: 20px;
}

.tree-view-content {
  height: calc(100vh - 100px);
}

.tree-panel, .document-panel {
  height: 100%;
}

.tree-card, .document-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.tree-container {
  padding: 10px;
  overflow-y: auto;
  flex: 1;
}

.document-container {
  padding: 10px;
  overflow-y: auto;
  flex: 1;
}

.highlight-info {
  margin-bottom: 15px;
}

.selected-path {
  margin-top: 5px;
  font-size: 14px;
}

.path-text {
  font-weight: bold;
  color: #409eff;
}

.document-content {
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fff;
  min-height: 500px;
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  font-size: 14px;
}

.node-value {
  color: #409eff;
  margin-left: 5px;
}
</style> 