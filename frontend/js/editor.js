/**
 * py-auto-api 可视化编辑器前端脚本
 */

class VisualEditor {
    constructor() {
        this.apiBase = '/api/v1';
        this.wsBase = 'ws://localhost:8000';
        this.socket = null;
        this.sessionId = null;
        this.currentSteps = [];
        this.selectedStepIndex = -1;
        this.browserSessionId = null;
        this.isRecording = false;
        this.recordingStartTime = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.createSession();
        this.connectWebSocket();
        this.loadTasks();
    }

    setupEventListeners() {
        // 录制控制
        document.getElementById('startRecording').addEventListener('click', () => this.startRecording());
        document.getElementById('stopRecording').addEventListener('click', () => this.stopRecording());
        document.getElementById('clearRecording').addEventListener('click', () => this.clearRecording());

        // 浏览器控制
        document.getElementById('launchBrowser').addEventListener('click', () => this.launchBrowser());
        document.getElementById('navigateUrl').addEventListener('click', () => this.navigateUrl());
        document.getElementById('takeScreenshot').addEventListener('click', () => this.takeScreenshot());
        document.getElementById('refreshBrowser').addEventListener('click', () => this.refreshBrowser());

        // 步骤操作
        document.getElementById('addStep').addEventListener('click', () => this.showAddStepModal());
        document.getElementById('editStep').addEventListener('click', () => this.editStep());
        document.getElementById('deleteStep').addEventListener('click', () => this.deleteStep());
        document.getElementById('reorderSteps').addEventListener('click', () => this.reorderSteps());

        // 任务管理
        document.getElementById('saveTask').addEventListener('click', () => this.showSaveTaskModal());
        document.getElementById('executeTask').addEventListener('click', () => this.executeTask());
        document.getElementById('previewTask').addEventListener('click', () => this.previewTask());
        document.getElementById('exportSteps').addEventListener('click', () => this.exportSteps());

        // 会话管理
        document.getElementById('newSession').addEventListener('click', () => this.createSession());
        document.getElementById('loadTask').addEventListener('click', () => this.showLoadTaskModal());

        // 模态框关闭
        document.querySelectorAll('.close').forEach(close => {
            close.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) this.hideModal(modal.id);
            });
        });

        // 模态框外部点击关闭
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal.id);
                }
            });
        });

        // URL输入框回车事件
        document.getElementById('urlInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.navigateUrl();
            }
        });
    }

    async createSession() {
        try {
            const response = await axios.post(`${this.apiBase}/editor/sessions`, {
                username: 'anonymous'
            });
            
            this.sessionId = response.data.session_id;
            this.updateSessionInfo();
            
            this.showToast('会话创建成功', 'success');
            
        } catch (error) {
            console.error('创建会话失败:', error);
            this.showToast('创建会话失败', 'error');
        }
    }

    connectWebSocket() {
        if (!this.sessionId) return;
        
        this.socket = io(`${this.wsBase}/editor/ws/${this.sessionId}`);
        
        this.socket.on('connect', () => {
            this.updateConnectionStatus('已连接');
            this.showToast('WebSocket连接成功', 'success');
        });
        
        this.socket.on('disconnect', () => {
            this.updateConnectionStatus('已断开');
            this.showToast('WebSocket连接断开', 'warning');
        });
        
        this.socket.on('message', (data) => {
            this.handleWebSocketMessage(data);
        });
        
        this.socket.on('steps_recorded', (data) => {
            this.showToast(`已记录 ${data.step_count} 个步骤`, 'info');
        });
        
        this.socket.on('recording_started', () => {
            this.updateRecordingStatus('录制中');
        });
        
        this.socket.on('recording_stopped', () => {
            this.updateRecordingStatus('已停止');
        });
    }

    handleWebSocketMessage(data) {
        console.log('WebSocket消息:', data);
        
        if (data.type === 'ping') {
            this.socket.emit('pong');
        }
    }

    async launchBrowser() {
        try {
            const response = await axios.post(`${this.apiBase}/automation/browser/launch`, {
                browser_type: 'chromium',
                headless: false,
                window_size: '1920x1080'
            });
            
            this.browserSessionId = response.data.session_id;
            this.updateBrowserStatus('已连接', 'connected');
            this.showToast('浏览器启动成功', 'success');
            
        } catch (error) {
            console.error('启动浏览器失败:', error);
            this.showToast('启动浏览器失败', 'error');
        }
    }

    async navigateUrl() {
        const url = document.getElementById('urlInput').value.trim();
        if (!url) {
            this.showToast('请输入URL', 'warning');
            return;
        }
        
        if (!this.browserSessionId) {
            this.showToast('请先启动浏览器', 'warning');
            return;
        }
        
        try {
            await axios.post(`${this.apiBase}/automation/browser/${this.browserSessionId}/navigate`, {
                url: url
            });
            
            this.showToast('导航成功', 'success');
            
        } catch (error) {
            console.error('导航失败:', error);
            this.showToast('导航失败', 'error');
        }
    }

    async takeScreenshot() {
        if (!this.browserSessionId) {
            this.showToast('请先启动浏览器', 'warning');
            return;
        }
        
        try {
            const response = await axios.get(`${this.apiBase}/automation/browser/${this.browserSessionId}/screenshot`);
            
            // 创建截图预览
            const screenshotWindow = window.open('', 'screenshot', 'width=800,height=600');
            screenshotWindow.document.write(`
                <html>
                    <head><title>截图预览</title></head>
                    <body style="margin:0;display:flex;justify-content:center;align-items:center;background:#f0f0f0;">
                        <img src="data:image/png;base64,${response.data.screenshot_base64}" 
                             style="max-width:100%;max-height:100%;box-shadow:0 0 20px rgba(0,0,0,0.3);" />
                    </body>
                </html>
            `);
            
            this.showToast('截图成功', 'success');
            
        } catch (error) {
            console.error('截图失败:', error);
            this.showToast('截图失败', 'error');
        }
    }

    async refreshBrowser() {
        if (!this.browserSessionId) {
            this.showToast('请先启动浏览器', 'warning');
            return;
        }
        
        try {
            // 重新加载页面
            await axios.post(`${this.apiBase}/automation/browser/${this.browserSessionId}/navigate`, {
                url: document.getElementById('urlInput').value
            });
            
            this.showToast('浏览器刷新成功', 'success');
            
        } catch (error) {
            console.error('刷新浏览器失败:', error);
            this.showToast('刷新浏览器失败', 'error');
        }
    }

    async startRecording() {
        if (this.isRecording) {
            this.showToast('录制已在进行中', 'warning');
            return;
        }
        
        if (!this.browserSessionId) {
            this.showToast('请先启动浏览器', 'warning');
            return;
        }
        
        try {
            const url = document.getElementById('urlInput').value.trim();
            const response = await axios.post(`${this.apiBase}/editor/record-steps/start`, {
                session_id: this.sessionId,
                target_url: url || null
            });
            
            this.isRecording = true;
            this.recordingStartTime = Date.now();
            this.updateRecordingControls();
            this.updateRecordingStatus('录制中');
            
            // 通知WebSocket
            if (this.socket) {
                this.socket.emit('recording_event', {
                    event_type: 'start',
                    timestamp: Date.now()
                });
            }
            
            this.showToast('开始录制', 'success');
            
        } catch (error) {
            console.error('开始录制失败:', error);
            this.showToast('开始录制失败', 'error');
        }
    }

    async stopRecording() {
        if (!this.isRecording) {
            this.showToast('当前未在录制', 'warning');
            return;
        }
        
        try {
            const response = await axios.post(`${this.apiBase}/editor/record-steps/stop`, {
                session_id: this.sessionId
            });
            
            this.isRecording = false;
            this.updateRecordingControls();
            this.updateRecordingStatus('已停止');
            
            // 通知WebSocket
            if (this.socket) {
                this.socket.emit('recording_event', {
                    event_type: 'stop',
                    timestamp: Date.now()
                });
            }
            
            // 重新加载步骤
            await this.loadRecordedSteps();
            
            const duration = ((Date.now() - this.recordingStartTime) / 1000).toFixed(1);
            this.showToast(`录制完成，持续 ${duration} 秒`, 'success');
            
        } catch (error) {
            console.error('停止录制失败:', error);
            this.showToast('停止录制失败', 'error');
        }
    }

    async clearRecording() {
        if (!confirm('确定要清除所有录制的步骤吗？')) {
            return;
        }
        
        try {
            await axios.delete(`${this.apiBase}/editor/recordings/${this.sessionId}`);
            
            this.currentSteps = [];
            this.updateStepList();
            this.updateStepControls();
            
            this.showToast('已清除录制步骤', 'success');
            
        } catch (error) {
            console.error('清除录制失败:', error);
            this.showToast('清除录制失败', 'error');
        }
    }

    async loadRecordedSteps() {
        try {
            const response = await axios.get(`${this.apiBase}/editor/recordings/${this.sessionId}`);
            this.currentSteps = response.data;
            this.updateStepList();
            this.updateStepControls();
            
        } catch (error) {
            console.error('加载录制步骤失败:', error);
        }
    }

    updateStepList() {
        const stepList = document.getElementById('stepList');
        const stepCount = document.getElementById('stepCount');
        
        if (this.currentSteps.length === 0) {
            stepList.innerHTML = `
                <div class="empty-state">
                    <p>尚未录制任何步骤</p>
                    <p>点击"开始录制"开始记录操作</p>
                </div>
            `;
            stepCount.textContent = '0 步骤';
            return;
        }
        
        stepCount.textContent = `${this.currentSteps.length} 步骤`;
        
        stepList.innerHTML = this.currentSteps.map((step, index) => `
            <div class="step-item ${index === this.selectedStepIndex ? 'selected' : ''}" 
                 data-index="${index}" onclick="editor.selectStep(${index})">
                <div class="step-header">
                    <div class="step-number">${index + 1}</div>
                    <div class="step-name">${step.step_name || `步骤 ${index + 1}`}</div>
                    <div class="step-type">${step.action_type}</div>
                </div>
                <div class="step-details">
                    ${step.target_selector ? `<p><span class="label">选择器:</span> ${step.target_selector}</p>` : ''}
                    ${step.target_text ? `<p><span class="label">文本:</span> ${step.target_text}</p>` : ''}
                    ${step.target_url ? `<p><span class="label">URL:</span> ${step.target_url}</p>` : ''}
                    ${step.wait_time ? `<p><span class="label">等待:</span> ${step.wait_time}ms</p>` : ''}
                </div>
            </div>
        `).join('');
    }

    selectStep(index) {
        this.selectedStepIndex = index;
        this.updateStepList();
        this.updateStepControls();
    }

    updateStepControls() {
        const hasSelection = this.selectedStepIndex >= 0;
        const hasSteps = this.currentSteps.length > 0;
        
        document.getElementById('editStep').disabled = !hasSelection;
        document.getElementById('deleteStep').disabled = !hasSelection;
        document.getElementById('reorderSteps').disabled = !hasSteps;
    }

    updateRecordingControls() {
        const startBtn = document.getElementById('startRecording');
        const stopBtn = document.getElementById('stopRecording');
        
        startBtn.disabled = this.isRecording;
        stopBtn.disabled = !this.isRecording;
    }

    updateBrowserStatus(status, className) {
        const statusElement = document.getElementById('browserStatus');
        statusElement.textContent = status;
        statusElement.className = `status-indicator ${className}`;
    }

    updateRecordingStatus(status) {
        document.getElementById('recordingStatus').textContent = `录制状态: ${status}`;
    }

    updateConnectionStatus(status) {
        document.getElementById('connectionStatus').textContent = `连接状态: ${status}`;
    }

    updateSessionInfo() {
        const sessionInfo = document.getElementById('sessionInfo');
        if (this.sessionId) {
            sessionInfo.textContent = `会话: ${this.sessionId.substring(0, 8)}...`;
        }
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type}`;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    showModal(modalId) {
        document.getElementById(modalId).classList.add('show');
    }

    hideModal(modalId) {
        document.getElementById(modalId).classList.remove('show');
    }

    showAddStepModal() {
        this.clearAddStepForm();
        this.showModal('addStepModal');
    }

    showSaveTaskModal() {
        this.clearSaveTaskForm();
        this.showModal('saveTaskModal');
    }

    showLoadTaskModal() {
        this.loadTasks();
        this.showModal('loadTaskModal');
    }

    clearAddStepForm() {
        document.getElementById('addStepForm').reset();
    }

    clearSaveTaskForm() {
        document.getElementById('saveTaskForm').reset();
        document.getElementById('taskUrl').value = document.getElementById('urlInput').value;
    }

    async loadTasks() {
        try {
            const response = await axios.get(`${this.apiBase}/tasks?limit=50`);
            this.displayTaskList(response.data);
        } catch (error) {
            console.error('加载任务列表失败:', error);
            this.showToast('加载任务列表失败', 'error');
        }
    }

    displayTaskList(tasks) {
        const taskList = document.getElementById('taskList');
        
        if (tasks.length === 0) {
            taskList.innerHTML = '<p>暂无任务</p>';
            return;
        }
        
        taskList.innerHTML = tasks.map(task => `
            <div class="task-item" style="padding: 1rem; border: 1px solid #e0e0e0; margin-bottom: 0.5rem; border-radius: 6px; cursor: pointer;" 
                 onclick="editor.loadTask(${task.id})">
                <h4 style="margin: 0 0 0.5rem 0; color: #333;">${task.name}</h4>
                <p style="margin: 0 0 0.5rem 0; color: #666; font-size: 0.9rem;">${task.description || '无描述'}</p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="background: #${this.getStatusColor(task.status)}; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">
                        ${this.getStatusText(task.status)}
                    </span>
                    <span style="color: #999; font-size: 0.8rem;">${task.url}</span>
                </div>
            </div>
        `).join('');
    }

    getStatusColor(status) {
        const colors = {
            'pending': 'ffc107',
            'running': '17a2b8',
            'completed': '28a745',
            'failed': 'dc3545',
            'cancelled': '6c757d'
        };
        return colors[status] || '6c757d';
    }

    getStatusText(status) {
        const texts = {
            'pending': '等待中',
            'running': '运行中',
            'completed': '已完成',
            'failed': '失败',
            'cancelled': '已取消'
        };
        return texts[status] || status;
    }

    async loadTask(taskId) {
        try {
            const response = await axios.get(`${this.apiBase}/tasks/${taskId}`);
            const task = response.data;
            
            // 加载任务信息到表单
            document.getElementById('taskName').value = task.name;
            document.getElementById('taskDescription').value = task.description || '';
            document.getElementById('taskUrl').value = task.url;
            document.getElementById('taskPriority').value = task.priority;
            
            // 加载任务的自动化步骤
            const stepsResponse = await axios.get(`${this.apiBase}/automation/steps/task/${taskId}`);
            this.currentSteps = stepsResponse.data;
            this.selectedStepIndex = -1;
            
            this.updateStepList();
            this.updateStepControls();
            
            // 关闭模态框
            this.hideModal('loadTaskModal');
            
            this.showToast(`已加载任务: ${task.name}`, 'success');
            
        } catch (error) {
            console.error('加载任务失败:', error);
            this.showToast('加载任务失败', 'error');
        }
    }

    async saveTask() {
        const taskData = {
            name: document.getElementById('taskName').value.trim(),
            description: document.getElementById('taskDescription').value.trim(),
            url: document.getElementById('taskUrl').value.trim(),
            priority: parseInt(document.getElementById('taskPriority').value)
        };
        
        if (!taskData.name || !taskData.url) {
            this.showToast('请填写任务名称和URL', 'warning');
            return;
        }
        
        try {
            const response = await axios.post(`${this.apiBase}/tasks`, taskData);
            const task = response.data;
            
            // 保存自动化步骤
            if (this.currentSteps.length > 0) {
                await this.saveTaskSteps(task.id);
            }
            
            this.hideModal('saveTaskModal');
            this.showToast(`任务保存成功: ${task.name}`, 'success');
            
        } catch (error) {
            console.error('保存任务失败:', error);
            this.showToast('保存任务失败', 'error');
        }
    }

    async saveTaskSteps(taskId) {
        try {
            for (let i = 0; i < this.currentSteps.length; i++) {
                const step = this.currentSteps[i];
                await axios.post(`${this.apiBase}/automation/steps`, {
                    task_id: taskId,
                    step_name: step.step_name || `步骤 ${i + 1}`,
                    step_order: i,
                    action_type: step.action_type,
                    target_selector: step.target_selector,
                    target_text: step.target_text,
                    target_url: step.target_url,
                    wait_time: step.wait_time || 0,
                    timeout: 30
                });
            }
            
            this.showToast('任务步骤保存成功', 'success');
            
        } catch (error) {
            console.error('保存任务步骤失败:', error);
            this.showToast('保存任务步骤失败', 'error');
        }
    }

    async executeTask() {
        if (this.currentSteps.length === 0) {
            this.showToast('请先保存任务', 'warning');
            return;
        }
        
        try {
            // 先保存任务
            await this.saveTask();
            
            // 获取刚保存的任务ID
            const tasksResponse = await axios.get(`${this.apiBase}/tasks?limit=1`);
            const task = tasksResponse.data[0];
            
            if (!task) {
                throw new Error('任务保存失败');
            }
            
            // 执行任务
            const response = await axios.post(`${this.apiBase}/tasks/${task.id}/execute`);
            
            this.showToast(`任务开始执行: ${response.data.execution_id}`, 'success');
            
        } catch (error) {
            console.error('执行任务失败:', error);
            this.showToast('执行任务失败', 'error');
        }
    }

    async previewTask() {
        if (this.currentSteps.length === 0) {
            this.showToast('请先录制或添加步骤', 'warning');
            return;
        }
        
        try {
            // 先保存任务
            await this.saveTask();
            
            // 获取刚保存的任务ID
            const tasksResponse = await axios.get(`${this.apiBase}/tasks?limit=1`);
            const task = tasksResponse.data[0];
            
            if (!task) {
                throw new Error('任务保存失败');
            }
            
            // 预览任务
            const response = await axios.post(`${this.apiBase}/automation/preview`, {
                task_id: task.id
            });
            
            this.showToast(`预览开始: ${response.data.preview_id}`, 'info');
            
        } catch (error) {
            console.error('预览任务失败:', error);
            this.showToast('预览任务失败', 'error');
        }
    }

    async exportSteps() {
        if (this.currentSteps.length === 0) {
            this.showToast('没有步骤可导出', 'warning');
            return;
        }
        
        try {
            const response = await axios.post(`${this.apiBase}/editor/export`, {
                session_id: this.sessionId,
                format: 'json'
            });
            
            // 下载JSON文件
            const dataStr = JSON.stringify(response.data, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `steps_export_${Date.now()}.json`;
            link.click();
            
            URL.revokeObjectURL(url);
            this.showToast('步骤导出成功', 'success');
            
        } catch (error) {
            console.error('导出步骤失败:', error);
            this.showToast('导出步骤失败', 'error');
        }
    }
}

// 全局函数，供HTML调用
function saveStep() {
    const form = document.getElementById('addStepForm');
    const formData = new FormData(form);
    
    const stepData = {
        step_name: document.getElementById('stepName').value,
        action_type: document.getElementById('actionType').value,
        target_selector: document.getElementById('targetSelector').value || null,
        target_text: document.getElementById('targetText').value || null,
        target_url: document.getElementById('targetUrl').value || null,
        wait_time: parseInt(document.getElementById('waitTime').value) || 0
    };
    
    editor.currentSteps.push(stepData);
    editor.updateStepList();
    editor.updateStepControls();
    
    editor.hideModal('addStepModal');
    editor.showToast('步骤添加成功', 'success');
}

function saveTask() {
    editor.saveTask();
}

function closeModal(modalId) {
    editor.hideModal(modalId);
}

// 键盘快捷键
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
            case 's':
                e.preventDefault();
                editor.showSaveTaskModal();
                break;
            case 'e':
                e.preventDefault();
                editor.executeTask();
                break;
            case 'r':
                e.preventDefault();
                if (editor.isRecording) {
                    editor.stopRecording();
                } else {
                    editor.startRecording();
                }
                break;
        }
    }
    
    if (e.key === 'Escape') {
        // 关闭模态框
        document.querySelectorAll('.modal.show').forEach(modal => {
            editor.hideModal(modal.id);
        });
    }
});

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.editor = new VisualEditor();
});

// 页面卸载时清理资源
window.addEventListener('beforeunload', () => {
    if (window.editor && window.editor.socket) {
        window.editor.socket.disconnect();
    }
});