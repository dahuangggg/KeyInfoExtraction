<template>
  <div class="home-container">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="upload-card">
          <div class="upload-area">
            <el-upload
              class="upload-component"
              drag
              :action="null"
              :http-request="customUpload"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
              :before-upload="beforeUpload"
              :show-file-list="false"
              multiple
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                拖拽文件到此处或 <em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持上传 PDF、DOCX、TXT 等格式文件，可同时选择多个文件批量上传
                </div>
              </template>
            </el-upload>
          </div>
          
          <div class="action-buttons">
            <el-button type="primary" @click="goToTreeView" :disabled="!currentDocumentId">
              <el-icon><connection /></el-icon>
              查看树状结构图
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row v-if="loading">
      <el-col :span="24" class="loading-container">
        <el-card>
          <div class="loading-content">
            <el-progress type="circle" :percentage="uploadProgress"></el-progress>
            <p class="loading-text">{{ loadingText }}</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" v-if="documentData && !loading">
      <el-col :span="24">
        <el-tabs v-model="activeTab" class="result-tabs">
          <el-tab-pane label="树状结构" name="tree">
            <el-card class="tree-card">
              <div class="tree-container">
                <el-tree
                  :data="treeData"
                  :props="defaultProps"
                  node-key="id"
                  default-expand-all
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
          </el-tab-pane>
          <el-tab-pane label="原文对比" name="compare">
            <el-card class="compare-card">
              <div class="compare-container">
                <div class="original-text">
                  <h3>原文内容</h3>
                  <div v-html="documentData.originalText"></div>
                </div>
                <div class="extracted-info">
                  <h3>提取信息</h3>
                  <pre>{{ JSON.stringify(documentData.extractedInfo, null, 2) }}</pre>
                </div>
              </div>
            </el-card>
          </el-tab-pane>
          <el-tab-pane label="JSON 数据" name="json">
            <el-card class="json-card">
              <div class="json-container">
                <pre>{{ JSON.stringify(documentData, null, 2) }}</pre>
              </div>
              <div class="export-actions">
                <el-button type="primary" @click="exportResult('json')">
                  <el-icon><download /></el-icon>
                  导出 JSON
                </el-button>
                <el-button type="success" @click="exportResult('csv')">
                  <el-icon><document /></el-icon>
                  导出 CSV
                </el-button>
              </div>
            </el-card>
          </el-tab-pane>
        </el-tabs>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Download, Document, Connection } from '@element-plus/icons-vue'
import { uploadDocument, uploadDocuments, exportDocumentResult } from '../api/document'
import { useRouter } from 'vue-router'
import historyService from '../services/history'

const documentData = ref(null)
const activeTab = ref('tree')
const loading = ref(false)
const uploadProgress = ref(0)
const loadingText = ref('正在上传文件...')
const currentDocumentId = ref(null)
const router = useRouter()
const currentFileName = ref('')

const defaultProps = {
  children: 'children',
  label: 'label'
}

// 将API返回的数据转换为树状结构
const treeData = computed(() => {
  if (!documentData.value) return []
  
  // 这里根据实际API返回的数据结构进行转换
  // 示例转换逻辑
  const convertToTreeData = (data, parentId = 0) => {
    let id = parentId
    const result = []
    
    if (typeof data !== 'object' || data === null) {
      return []
    }
    
    Object.entries(data).forEach(([key, value]) => {
      id++
      const node = {
        id,
        label: key
      }
      
      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        node.children = convertToTreeData(value, id)
      } else if (Array.isArray(value)) {
        if (value.length > 0 && typeof value[0] === 'object') {
          node.children = value.map((item, index) => {
            const arrayId = id * 1000 + index
            return {
              id: arrayId,
              label: `[${index}]`,
              children: convertToTreeData(item, arrayId)
            }
          })
        } else {
          node.value = JSON.stringify(value)
        }
      } else {
        node.value = value
      }
      
      result.push(node)
    })
    
    return result
  }
  
  return convertToTreeData(documentData.value.extractedInfo)
})

const beforeUpload = (file) => {
  const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
  const isAllowed = allowedTypes.includes(file.type)
  
  if (!isAllowed) {
    ElMessage.error('只支持 PDF、DOCX 和 TXT 格式文件!')
    return false
  }
  
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB!')
    return false
  }
  
  return true
}

const customUpload = async (options) => {
  const { file, fileList } = options
  loading.value = true
  uploadProgress.value = 0
  
  // 判断是否为批量上传
  const isBatchUpload = fileList && fileList.length > 1
  
  if (isBatchUpload) {
    loadingText.value = `正在批量上传 ${fileList.length} 个文件...`
    currentFileName.value = `${fileList.length} 个文件`
  } else {
    loadingText.value = '正在上传文件...'
    currentFileName.value = file.name
  }
  
  try {
    // 模拟上传进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 300)
    
    let response
    
    // 根据是否为批量上传调用不同的API
    if (isBatchUpload) {
      response = await uploadDocuments(fileList)
    } else {
      response = await uploadDocument(file)
    }
    
    clearInterval(progressInterval)
    uploadProgress.value = 100
    
    if (isBatchUpload) {
      loadingText.value = `${response.data.successful}/${response.data.total} 个文件处理完成!`
    } else {
      loadingText.value = '文件处理完成!'
    }
    
    setTimeout(() => {
      loading.value = false
      options.onSuccess(response)
    }, 500)
    
  } catch (error) {
    loading.value = false
    options.onError(error)
  }
}

const handleUploadSuccess = (response) => {
  // 判断是否为批量上传响应
  const isBatchResponse = response.data && response.data.total !== undefined
  
  if (isBatchResponse) {
    const { total, successful, documents } = response.data
    
    if (successful > 0) {
      ElMessage.success(`成功上传 ${successful}/${total} 个文件`)
      
      // 如果有成功上传的文档，显示第一个文档
      if (documents && documents.length > 0) {
        documentData.value = documents[0]
        currentDocumentId.value = documents[0].id
        activeTab.value = 'tree'
        
        // 添加操作记录
        addOperationHistory({
          description: `批量上传文档：成功 ${successful}/${total} 个文件`,
          type: 'success'
        })
        
        // 如果只有一个文档成功上传，提示是否查看树状图
        if (successful === 1) {
          ElMessageBox.confirm(
            '文件上传成功，是否查看树状结构图？',
            '提示',
            {
              confirmButtonText: '查看',
              cancelButtonText: '留在当前页面',
              type: 'success',
            }
          )
            .then(() => {
              // 跳转到树状结构图页面
              router.push(`/tree-view/${currentDocumentId.value}`)
            })
            .catch(() => {
              // 用户选择留在当前页面，不做处理
            })
        } else {
          // 多个文档上传成功，提示用户去历史记录查看
          ElMessageBox.alert(
            '多个文件上传成功，可在历史记录中查看所有文档',
            '批量上传完成',
            {
              confirmButtonText: '确定',
              type: 'success',
            }
          )
        }
      }
    } else {
      ElMessage.error('所有文件上传失败，请重试')
    }
  } else {
    // 单文件上传的处理逻辑（保持原有代码）
    ElMessage.success('文件上传成功')
    documentData.value = response.data
    currentDocumentId.value = response.data.id
    activeTab.value = 'tree'
    
    // 添加操作记录
    addOperationHistory({
      description: `上传文档：${currentFileName.value}`,
      type: 'success'
    })
    
    // 添加查看树状结构图按钮
    ElMessageBox.confirm(
      '文件上传成功，是否查看树状结构图？',
      '提示',
      {
        confirmButtonText: '查看',
        cancelButtonText: '留在当前页面',
        type: 'success',
      }
    )
      .then(() => {
        // 跳转到树状结构图页面
        router.push(`/tree-view/${currentDocumentId.value}`)
      })
      .catch(() => {
        // 用户选择留在当前页面，不做处理
      })
  }
}

const handleUploadError = () => {
  ElMessage.error('文件上传失败，请重试')
}

const handleNodeClick = (data) => {
  console.log(data)
}

const exportResult = async (format) => {
  if (!currentDocumentId.value) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  
  try {
    const response = await exportDocumentResult(currentDocumentId.value, format)
    
    // 创建下载链接
    const blob = new Blob([response.data])
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `document_${currentDocumentId.value}.${format}`
    link.click()
    
    // 添加操作记录
    addOperationHistory({
      description: `导出${format.toUpperCase()}数据`,
      type: 'info'
    })
    
    ElMessage.success(`成功导出为 ${format.toUpperCase()} 格式`)
  } catch (error) {
    ElMessage.error('导出失败，请重试')
    console.error(error)
  }
}

// 跳转到树状结构图页面
const goToTreeView = () => {
  if (currentDocumentId.value) {
    router.push(`/tree-view/${currentDocumentId.value}`)
  } else {
    ElMessage.warning('请先上传文档')
  }
}

// 添加操作记录
const addOperationHistory = (operation) => {
  historyService.addOperation(operation)
}
</script>

<style scoped>
.home-container {
  padding: 20px;
}

.upload-card {
  margin-bottom: 20px;
}

.upload-area {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.upload-component {
  width: 100%;
  max-width: 600px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.loading-container {
  margin-bottom: 20px;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px;
}

.loading-text {
  margin-top: 15px;
  font-size: 16px;
  color: #409eff;
}

.result-tabs {
  margin-top: 20px;
}

.tree-card,
.compare-card,
.json-card {
  min-height: 400px;
}

.tree-container {
  padding: 10px;
}

.compare-container {
  display: flex;
  gap: 20px;
}

.original-text,
.extracted-info {
  flex: 1;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  max-height: 600px;
  overflow-y: auto;
}

.json-container {
  max-height: 600px;
  overflow-y: auto;
  padding: 10px;
}

.export-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 20px;
  padding: 10px;
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