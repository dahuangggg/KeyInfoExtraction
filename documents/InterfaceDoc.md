# 关键信息提取系统接口文档

## API 前缀

所有API端点都以 `/api/v1` 为前缀

## 文档管理

### 上传文档： POST /api/v1/documents

传入：
```
文件表单数据:
files: 文件列表，支持 .doc, .docx 格式
```

返回：
```json
{
    "total": 上传的文件总数,
    "successful": 成功上传的文件数,
    "documents": [
        {
            "id": 文档ID,
            "filename": 系统内部文件名,
            "original_filename": 原始文件名,
            "file_path": 文件路径,
            "file_size": 文件大小(字节),
            "file_type": 文件类型,
            "upload_time": 上传时间,
            "processed": 是否已处理
        },
        ...
    ]
}
```

### 获取文档列表： GET /api/v1/documents

传入：
```
查询参数：
skip: 分页偏移量 (默认值: 0)
limit: 分页大小 (默认值: 100, 最大值: 1000)
```

返回：
```json
[
    {
        "id": 文档ID,
        "original_filename": 原始文件名,
        "file_type": 文件类型,
        "file_size": 文件大小(字节),
        "upload_time": 上传时间,
        "processed": 是否已处理,
        "processing_time": 处理耗时(秒，可能为空)
    },
    ...
]
```

### 获取文档详情： GET /api/v1/documents/{document_id}

传入：
```
路径参数：
document_id: 文档ID
```

返回：
```json
{
    "id": 文档ID,
    "filename": 系统内部文件名,
    "original_filename": 原始文件名,
    "file_path": 文件路径,
    "file_size": 文件大小(字节),
    "file_type": 文件类型,
    "upload_time": 上传时间,
    "processed": 是否已处理,
    "process_start_time": 处理开始时间,
    "process_end_time": 处理结束时间,
    "processing_time": 处理耗时(秒)
}
```

### 获取文档内容： GET /api/v1/documents/content/{document_id}

传入：
```
路径参数：
document_id: 文档ID
```

返回：
```json
{
    "document_id": 文档ID,
    "filename": "原始文件名",
    "content": "文档提取后的文本内容"
}
```

### 删除文档： DELETE /api/v1/documents/{document_id}

传入：
```
路径参数：
document_id: 文档ID
```

返回：
```json
{
    "success": true/false
}
```

## 信息提取

### 创建提取任务： POST /api/v1/extraction

传入：
```json
{
    "document_id": 文档ID
}
```

返回：
```json
{
    "status": "processing",
    "document_id": 文档ID,
    "message": "文档处理已开始，请稍后查询结果"
}
```

### 获取提取结果： GET /api/v1/extraction/{document_id}

传入：
```
路径参数：
document_id: 文档ID

查询参数：
format: 可选参数，指定为"xlsx"时返回Excel文件
```

返回：
```json
{
    "元器件物理状态分析": [
        {
            "物理状态组": "组名称",
            "物理状态项": [
                {
                    "物理状态名称": "状态名称",
                    "典型物理状态值": "状态值",
                    "禁限用信息": "禁限用信息",
                    "测试评语": "测试评语",
                    "试验项目": "试验项目"
                },
                ...
            ]
        },
        ...
    ],
    "其他提取内容...": "..."
}
```

注：当format=xlsx时，返回Excel文件而非JSON

### 更新提取结果： PUT /api/v1/extraction/{document_id}

传入：
```json
{
    "groups": [
        {
            "物理状态组": "组名称",
            "物理状态项": [
                {
                    "物理状态名称": "状态名称",
                    "典型物理状态值": "新状态值",
                    "禁限用信息": "新禁限用信息",
                    "测试评语": "新测试评语",
                    "试验项目": "试验项目"
                },
                ...
            ]
        },
        ...
    ]
}
```

> **重要说明**：此接口采用**完全覆盖**策略，发送的数据将替换原有的所有物理状态组和物理状态项。请确保在调用此接口时传入完整的数据结构，而不仅是变更部分。

返回：更新后的完整提取结果，与获取提取结果接口返回格式相同

### 测试提取功能： POST /api/v1/extraction/test

传入：
```
文件表单数据:
file: 单个文件，支持 .doc, .docx 格式
```

返回：
```json
{
    "status": "success",
    "filename": "文件名",
    "results": {
        "元器件物理状态分析": [
            {
                "物理状态组": "组名称",
                "物理状态项": [
                    {
                        "物理状态名称": "状态名称",
                        "典型物理状态值": "状态值",
                        "禁限用信息": "禁限用信息",
                        "测试评语": "测试评语",
                        "试验项目": "试验项目"
                    },
                    ...
                ]
            },
            ...
        ],
        "其他提取内容...": "..."
    }
}
```

### 批量处理文档： POST /api/v1/extraction/batch

传入：
```
查询参数：
limit: 最大处理文档数量 (默认: 10, 最大: 100)
```

返回：
```json
{
    "status": "success",
    "message": "开始处理 x 个文档，处理将在后台进行",
    "processing_document_ids": [文档ID1, 文档ID2, ...],
    "processed_count": 处理的文档数量
}
```

## 编辑历史

### 获取文档编辑历史： GET /api/v1/edit-history/{document_id}

传入：
```
路径参数：
document_id: 文档ID

查询参数：
skip: 分页偏移量 (默认: 0)
limit: 分页大小 (默认: 100)
```

返回：
```json
[
    {
        "id": 历史记录ID,
        "document_id": 文档ID,
        "edit_time": 编辑时间,
        "entity_type": "实体类型",
        "entity_id": 实体ID,
        "field_name": "字段名称",
        "old_value": "旧值",
        "new_value": "新值"
    },
    ...
]
```

### 回溯到历史记录点： POST /api/v1/edit-history/{document_id}/revert/{history_id}

传入：
```
路径参数：
document_id: 文档ID
history_id: 历史记录ID
```

返回：回溯后的完整提取结果，与获取提取结果接口返回格式相同

## 知识库管理

### 从文档创建知识库条目： POST /api/v1/knowledge-base/{document_id}

传入：
```
路径参数：
document_id: 文档ID
```

返回：
```json
{
    "success": true,
    "imported_count": 导入的条目数量
}
```

## 数据交互格式说明

### 提取结果格式

提取结果采用JSON格式，主要包含以下字段：

```json
{
    "元器件物理状态分析": [
        {
            "物理状态组": "组名称",
            "物理状态项": [
                {
                    "物理状态名称": "状态名称",
                    "典型物理状态值": "状态值",
                    "禁限用信息": "禁限用信息",
                    "测试评语": "测试评语",
                    "试验项目": "试验项目"
                }
            ]
        }
    ]
}
```

说明：
1. `元器件物理状态分析`是结果的顶层键，包含多个物理状态组。
2. 每个物理状态组由`物理状态组`名称和`物理状态项`数组组成。
3. 每个物理状态项包含以下字段：
   - `物理状态名称`：物理状态的名称
   - `典型物理状态值`：物理状态的典型值
   - `禁限用信息`：是否禁用或限用，可用值包括"可用"、"限用"、"禁用"和"/"
   - `测试评语`：测试相关评价
   - `试验项目`：相关的试验项目

### 编辑数据操作说明

使用PUT `/api/v1/extraction/{document_id}`更新提取结果时，后端将采用**完全覆盖**策略：

1. 后端会首先删除所有现有的物理状态组和物理状态项
2. 然后根据传入的JSON数据创建全新的记录
3. 同时记录编辑历史以支持后续的撤销操作
