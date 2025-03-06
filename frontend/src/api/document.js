import axios from 'axios'

// 是否使用模拟数据（开发环境）
const useMockData = true

// 模拟数据
const mockData = {
  documents: [
    {
      id: 'doc-001',
      title: '结构分析报告',
      uploadTime: '2023-05-15 10:30:00',
      originalText: `
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
      `,
      extractedInfo: {
        基本信息: {
          文档标题: '结构分析报告',
          文档编号: 'CA15110',
          创建日期: '2023-05-15'
        },
        结构参数: {
          材料: '铝合金',
          尺寸: {
            长度: '120mm',
            宽度: '80mm',
            高度: '25mm'
          },
          重量: '350g'
        },
        测试结果: {
          强度测试: '通过',
          疲劳测试: '通过',
          温度测试: '部分通过'
        }
      }
    }
  ]
}

/**
 * 上传文档并提取信息
 * @param {File} file - 要上传的文件
 * @returns {Promise} - 返回提取结果的Promise
 */
export const uploadDocument = (file) => {
  if (useMockData) {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          data: mockData.documents[0]
        })
      }, 1500)
    })
  }
  
  const formData = new FormData()
  formData.append('file', file)
  
  return axios.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 获取文档处理历史记录
 * @param {Object} params - 查询参数
 * @returns {Promise} - 返回历史记录的Promise
 */
export const getDocumentHistory = (params = {}) => {
  if (useMockData) {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          data: {
            documents: mockData.documents
          }
        })
      }, 300)
    })
  }
  
  return axios.get('/documents/history', { params })
}

/**
 * 获取单个文档的详细信息
 * @param {string} documentId - 文档ID
 * @returns {Promise} - 返回文档详情的Promise
 */
export const getDocumentDetail = (documentId) => {
  if (useMockData) {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          data: mockData.documents[0]
        })
      }, 300)
    })
  }
  
  return axios.get(`/documents/${documentId}`)
}

/**
 * 删除文档
 * @param {string} documentId - 文档ID
 * @returns {Promise} - 返回删除结果的Promise
 */
export const deleteDocument = (documentId) => {
  if (useMockData) {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          data: { success: true }
        })
      }, 300)
    })
  }
  
  return axios.delete(`/documents/${documentId}`)
}

/**
 * 导出文档提取结果
 * @param {string} documentId - 文档ID
 * @param {string} format - 导出格式 (json, csv, etc.)
 * @returns {Promise} - 返回导出结果的Promise
 */
export const exportDocumentResult = (documentId, format = 'json') => {
  if (useMockData) {
    return new Promise((resolve) => {
      setTimeout(() => {
        const data = format === 'json' 
          ? JSON.stringify(mockData.documents[0], null, 2)
          : 'key,value\n文档标题,结构分析报告\n文档编号,CA15110\n创建日期,2023-05-15'
        
        resolve({
          data: new Blob([data], { type: format === 'json' ? 'application/json' : 'text/csv' })
        })
      }, 300)
    })
  }
  
  return axios.get(`/documents/${documentId}/export`, {
    params: { format },
    responseType: 'blob'
  })
} 