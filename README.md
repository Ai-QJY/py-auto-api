# py-auto-api

一个完整的网站自动化工具，支持可视化编辑来自动化任何网站的操作。

## 功能特性

- 🌐 **API驱动**：通过RESTful API接收任务参数
- 📝 **可视化编辑器**：Web界面记录网站操作步骤
- 🤖 **智能自动化**：支持批量执行任务
- 📊 **结果追踪**：实时返回执行结果
- ⚡ **高性能**：基于现代技术栈构建

## 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行服务
```bash
cd backend
uvicorn main:app --reload
```

### 使用API
1. 发送POST请求到 `/api/tasks`
2. 在可视化编辑器中记录操作步骤
3. 批量执行任务并获取结果

## 项目结构

```
py-auto-api/
├── backend/           # FastAPI后端
├── frontend/          # 可视化编辑器
├── automation/        # 浏览器自动化核心
├── storage/           # 数据存储层
└── requirements.txt   # 依赖管理
```

## API文档

启动服务后访问：`http://localhost:8000/docs`

## 许可证

MIT License