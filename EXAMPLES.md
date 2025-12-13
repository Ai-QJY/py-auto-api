# py-auto-api 使用示例

本示例展示如何使用 py-auto-api 创建和执行自动化任务。

## 1. 启动服务

```bash
# 克隆或下载项目后
cd py-auto-api

# 运行启动脚本
chmod +x start.sh
./start.sh
```

## 2. 访问可视化编辑器

打开浏览器访问：http://localhost:8000/editor

## 3. API 使用示例

### 创建任务

```python
import requests

# 创建任务
response = requests.post('http://localhost:8000/api/v1/tasks', json={
    "name": "百度搜索测试",
    "description": "在百度搜索关键词并获取结果",
    "url": "https://www.baidu.com",
    "priority": 1
})

task = response.json()
print(f"任务创建成功，ID: {task['id']}")
```

### 添加自动化步骤

```python
# 添加自动化步骤
steps = [
    {
        "task_id": task['id'],
        "step_name": "搜索输入",
        "step_order": 0,
        "action_type": "click",
        "target_selector": "#kw",
        "wait_time": 1000
    },
    {
        "task_id": task['id'],
        "step_name": "输入搜索关键词",
        "step_order": 1,
        "action_type": "type",
        "target_selector": "#kw",
        "target_text": "py-auto-api",
        "wait_time": 1000
    },
    {
        "task_id": task['id'],
        "step_name": "点击搜索",
        "step_order": 2,
        "action_type": "click",
        "target_selector": "#su",
        "wait_time": 2000
    }
]

for step in steps:
    response = requests.post('http://localhost:8000/api/v1/automation/steps', json=step)
    print(f"步骤创建: {step['step_name']}")
```

### 执行任务

```python
# 执行任务
response = requests.post(f'http://localhost:8000/api/v1/tasks/{task["id"]}/execute')
result = response.json()
print(f"任务执行ID: {result['execution_id']}")
```

### 批量执行任务

```python
# 批量执行多个任务
task_ids = [1, 2, 3]  # 任务ID列表
response = requests.post('http://localhost:8000/api/v1/tasks/batch/execute', json={
    "task_ids": task_ids
})
result = response.json()
print(f"批量执行ID: {result['execution_id']}")
```

### 获取任务状态

```python
# 检查任务状态
response = requests.get(f'http://localhost:8000/api/v1/tasks/{task["id"]}/status')
status = response.json()
print(f"任务状态: {status['status']}")
print(f"进度: {status['progress']}%")
```

## 4. 浏览器自动化操作

### 启动浏览器会话

```python
# 启动浏览器
response = requests.post('http://localhost:8000/api/v1/automation/browser/launch', json={
    "browser_type": "chromium",
    "headless": False,
    "window_size": "1920x1080"
})
session = response.json()
session_id = session['session_id']
```

### 导航到URL

```python
# 浏览器导航
response = requests.post(f'http://localhost:8000/api/v1/automation/browser/{session_id}/navigate', json={
    "url": "https://example.com"
})
result = response.json()
print(f"页面标题: {result['title']}")
```

### 截图

```python
# 获取截图
response = requests.get(f'http://localhost:8000/api/v1/automation/browser/{session_id}/screenshot')
screenshot = response.json()
print(f"截图数据长度: {len(screenshot['screenshot_base64'])} 字符")
```

## 5. 可视化编辑器API

### 创建编辑器会话

```python
# 创建编辑器会话
response = requests.post('http://localhost:8000/api/v1/editor/sessions', json={
    "username": "test_user",
    "task_id": task['id']
})
session = response.json()
editor_session_id = session['session_id']
```

### 记录步骤

```python
# 记录操作步骤
steps = [
    {
        "action_type": "click",
        "target_selector": ".search-button",
        "timestamp": 1234567890.123,
        "wait_after": 1000
    },
    {
        "action_type": "type",
        "target_selector": ".search-input",
        "target_text": "test query",
        "timestamp": 1234567891.456,
        "wait_after": 500
    }
]

response = requests.post('http://localhost:8000/api/v1/editor/record-steps', json={
    "session_id": editor_session_id,
    "steps": steps
})
result = response.json()
print(f"已记录 {result['recorded_steps']} 个步骤")
```

## 6. WebSocket 实时通信

```javascript
// 前端WebSocket连接
const socket = io('ws://localhost:8000/editor/ws/' + session_id);

socket.on('connect', () => {
    console.log('WebSocket连接成功');
});

socket.on('steps_recorded', (data) => {
    console.log(`已记录 ${data.step_count} 个步骤`);
});

socket.on('recording_event', (data) => {
    console.log('录制事件:', data.event_type);
});

// 发送消息
socket.emit('ping');
```

## 7. 数据导出和导入

### 导出录制的步骤

```python
# 导出步骤为JSON格式
response = requests.post('http://localhost:8000/api/v1/editor/export', json={
    "session_id": editor_session_id,
    "format": "json"
})
export_data = response.json()

# 保存到文件
with open('steps_export.json', 'w') as f:
    import json
    json.dump(export_data, f, indent=2)
```

### 导出为自动化任务

```python
# 导出为自动化步骤格式
response = requests.post('http://localhost:8000/api/v1/editor/export', json={
    "session_id": editor_session_id,
    "format": "automation"
})
automation_data = response.json()

# 创建新的自动化任务
for step in automation_data['steps']:
    step['task_id'] = new_task_id
    requests.post('http://localhost:8000/api/v1/automation/steps', json=step)
```

## 8. 错误处理和调试

### 常见错误处理

```python
import requests
from requests.exceptions import RequestException

def execute_with_retry(task_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(f'http://localhost:8000/api/v1/tasks/{task_id}/execute', timeout=30)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            print(f"尝试 {attempt + 1} 失败: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # 指数退避
```

### 检查服务状态

```python
# 检查服务健康状态
try:
    response = requests.get('http://localhost:8000/', timeout=5)
    if response.status_code == 200:
        print("✅ 服务正常运行")
    else:
        print(f"❌ 服务返回状态码: {response.status_code}")
except RequestException as e:
    print(f"❌ 服务不可用: {e}")
```

## 9. 高级功能

### 任务调度

```python
# 获取任务统计信息
response = requests.get('http://localhost:8000/api/v1/tasks/stats/overview')
stats = response.json()
print(f"总任务数: {stats['total_tasks']}")
print(f"成功率: {stats['success_rate']}%")
```

### 批量操作

```python
# 批量删除任务
response = requests.post('http://localhost:8000/api/v1/tasks/batch/delete', json={
    "operation": "delete",
    "task_ids": [1, 2, 3]
})
result = response.json()
print(f"删除完成: {result['success_count']}/{result['total_count']}")
```

这个示例涵盖了 py-auto-api 的主要功能和使用方法。您可以根据具体需求调整和扩展这些示例代码。