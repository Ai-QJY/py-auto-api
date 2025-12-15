"""
Pydantic数据验证模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(str, Enum):
    """操作类型枚举"""
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    NAVIGATE = "navigate"
    SCREENSHOT = "screenshot"
    HOVER = "hover"
    DRAG_DROP = "drag_drop"
    SELECT = "select"
    UPLOAD = "upload"


# Task相关模式
class TaskBase(BaseModel):
    """任务基础模式"""
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    url: str = Field(..., description="目标URL")
    priority: int = Field(0, description="任务优先级")
    parameters: Optional[Dict[str, Any]] = Field(None, description="任务参数")


class TaskCreate(TaskBase):
    """创建任务模式"""
    pass


class TaskUpdate(BaseModel):
    """更新任务模式"""
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None


class TaskResponse(TaskBase):
    """任务响应模式"""
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    execution_count: int
    success_count: int
    failure_count: int
    
    class Config:
        from_attributes = True


# Automation Step相关模式
class AutomationStepBase(BaseModel):
    """自动化步骤基础模式"""
    step_name: str = Field(..., description="步骤名称")
    step_order: int = Field(..., description="步骤顺序")
    action_type: ActionType = Field(..., description="操作类型")
    target_selector: Optional[str] = Field(None, description="目标选择器")
    target_text: Optional[str] = Field(None, description="目标文本")
    target_url: Optional[str] = Field(None, description="目标URL")
    parameters: Optional[Dict[str, Any]] = Field(None, description="步骤参数")
    wait_time: int = Field(0, description="等待时间(毫秒)")
    timeout: int = Field(30, description="超时时间(秒)")


class AutomationStepCreate(AutomationStepBase):
    """创建自动化步骤模式"""
    task_id: int = Field(..., description="关联任务ID")


class AutomationStepUpdate(BaseModel):
    """更新自动化步骤模式"""
    step_name: Optional[str] = None
    step_order: Optional[int] = None
    action_type: Optional[ActionType] = None
    target_selector: Optional[str] = None
    target_text: Optional[str] = None
    target_url: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    wait_time: Optional[int] = None
    timeout: Optional[int] = None


class AutomationStepResponse(AutomationStepBase):
    """自动化步骤响应模式"""
    id: int
    task_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# 执行相关模式
class ExecutionRequest(BaseModel):
    """执行请求模式"""
    task_ids: List[int] = Field(..., description="要执行的任务ID列表")
    force_restart: bool = Field(False, description="强制重启")
    batch_size: int = Field(1, description="批处理大小")
    parallel_execution: bool = Field(False, description="并行执行")


class ExecutionResponse(BaseModel):
    """执行响应模式"""
    execution_id: str = Field(..., description="执行ID")
    status: str = Field(..., description="执行状态")
    total_tasks: int = Field(..., description="总任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    failed_tasks: int = Field(..., description="失败任务数")
    estimated_time: Optional[int] = Field(None, description="预计时间(秒)")


class ExecutionStatus(BaseModel):
    """执行状态模式"""
    execution_id: str
    task_id: int
    status: TaskStatus
    current_step: Optional[str]
    progress: float = Field(..., ge=0, le=100)
    start_time: datetime
    estimated_completion: Optional[datetime]
    results: Optional[Dict[str, Any]]


# 编辑器相关模式
class EditorSessionCreate(BaseModel):
    """创建编辑器会话模式"""
    task_id: Optional[int] = Field(None, description="关联任务ID")
    username: Optional[str] = Field(None, description="用户名")


class EditorSessionResponse(BaseModel):
    """编辑器会话响应模式"""
    session_id: str
    task_id: Optional[int]
    current_url: Optional[str]
    created_at: datetime
    temp_data: Optional[Dict[str, Any]]


class RecordedStep(BaseModel):
    """记录的步骤模式"""
    action_type: ActionType
    target_selector: Optional[str] = None
    target_text: Optional[str] = None
    x_path: Optional[str] = None
    coordinates: Optional[Dict[str, int]] = None
    timestamp: float
    wait_after: int = Field(0, description="操作后等待时间")


class StepRecordingRequest(BaseModel):
    """步骤录制请求模式"""
    session_id: str
    steps: List[RecordedStep]


# 实时通信模式
class WebSocketMessage(BaseModel):
    """WebSocket消息模式"""
    type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())


# 批量操作模式
class BatchOperationRequest(BaseModel):
    """批量操作请求模式"""
    operation: str = Field(..., description="操作类型")
    task_ids: List[int] = Field(..., description="任务ID列表")
    parameters: Optional[Dict[str, Any]] = Field(None, description="操作参数")


class BatchOperationResponse(BaseModel):
    """批量操作响应模式"""
    operation_id: str
    total_count: int
    success_count: int
    failure_count: int
    results: List[Dict[str, Any]]


# 浏览器配置模式
class BrowserConfig(BaseModel):
    """浏览器配置模式"""
    browser_type: str = Field(default="chrome", description="浏览器类型")
    headless: bool = Field(default=True, description="无头模式")
    window_size: str = Field(default="1920x1080", description="窗口大小")
    user_agent: Optional[str] = Field(None, description="用户代理")
    proxy_url: Optional[str] = Field(None, description="代理URL")
    timeout: int = Field(default=30, description="超时时间(秒)")