# 文档关键信息提取系统 - 前端

这是文档关键信息提取系统的前端部分，基于Vue 3和Element Plus构建。

## 技术栈

- **Vue 3**: 渐进式JavaScript框架
- **Element Plus**: 基于Vue 3的组件库
- **Vue Router**: 官方路由管理器
- **Axios**: 基于Promise的HTTP客户端
- **Vite**: 下一代前端构建工具

## 项目结构

```
frontend/
├── public/             # 静态资源
├── src/
│   ├── api/            # API服务
│   ├── assets/         # 资源文件
│   ├── components/     # 公共组件
│   ├── router/         # 路由配置
│   ├── views/          # 页面组件
│   ├── App.vue         # 根组件
│   └── main.js         # 入口文件
├── .env                # 环境变量
├── index.html          # HTML模板
├── package.json        # 项目配置
└── vite.config.js      # Vite配置
```

## 功能特性

- 文档上传与处理
- 树状结构展示提取的信息
- 原文与提取信息对比
- JSON数据查看与导出
- 响应式设计，适配不同设备

## 开发指南

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 与后端集成

前端通过API与后端服务进行通信，主要包括：

- 文档上传与处理
- 获取处理结果
- 导出数据

API请求配置在`src/api`目录下，可根据实际后端API进行调整。 