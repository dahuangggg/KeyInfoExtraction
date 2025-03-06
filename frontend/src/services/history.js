import { ref } from 'vue'

// 创建一个响应式的操作历史记录数组
const operationHistory = ref([])

// 生成唯一ID
let nextId = 1

/**
 * 添加操作记录
 * @param {Object} operation - 操作信息
 * @param {string} operation.description - 操作描述
 * @param {string} operation.type - 操作类型 (success, info, warning, danger)
 * @returns {number} - 操作ID
 */
function addOperation(operation) {
  const id = nextId++
  const timestamp = new Date().toLocaleString()
  
  const newOperation = {
    id,
    description: operation.description,
    timestamp,
    type: operation.type || 'info',
    undone: false
  }
  
  operationHistory.value.unshift(newOperation)
  
  // 限制历史记录数量，最多保留50条
  if (operationHistory.value.length > 50) {
    operationHistory.value.pop()
  }
  
  return id
}

/**
 * 撤销操作
 * @param {number} id - 操作ID
 * @returns {boolean} - 是否成功撤销
 */
function undoOperation(id) {
  const index = operationHistory.value.findIndex(item => item.id === id)
  if (index !== -1 && !operationHistory.value[index].undone) {
    operationHistory.value[index].undone = true
    return true
  }
  return false
}

/**
 * 重做操作
 * @param {number} id - 操作ID
 * @returns {boolean} - 是否成功重做
 */
function redoOperation(id) {
  const index = operationHistory.value.findIndex(item => item.id === id)
  if (index !== -1 && operationHistory.value[index].undone) {
    operationHistory.value[index].undone = false
    return true
  }
  return false
}

/**
 * 清空操作历史
 */
function clearHistory() {
  operationHistory.value = []
}

/**
 * 获取操作历史记录
 * @returns {Array} - 操作历史记录数组
 */
function getHistory() {
  return operationHistory.value
}

// 创建服务对象
const historyService = {
  addOperation,
  undoOperation,
  redoOperation,
  clearHistory,
  getHistory
}

// 默认导出服务对象
export default historyService 