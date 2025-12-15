"""
数据模型定义
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List, Dict, Any

Base = declarative_base()


class Task(Base):
    """任务模型"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    
    # 任务状态
    status = Column(String, default="pending")  # pending, running, completed, failed
    priority = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 执行结果
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 任务参数
    parameters = Column(JSON, nullable=True)
    
    # 执行统计
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)


class AutomationStep(Base):
    """自动化步骤模型"""
    __tablename__ = "automation_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)
    
    # 步骤信息
    step_name = Column(String, nullable=False)
    step_order = Column(Integer, nullable=False)
    
    # 操作类型
    action_type = Column(String, nullable=False)  # click, type, scroll, wait, etc.
    target_selector = Column(String, nullable=True)
    target_text = Column(String, nullable=True)
    target_url = Column(String, nullable=True)
    
    # 步骤参数
    parameters = Column(JSON, nullable=True)
    
    # 时间信息
    wait_time = Column(Integer, default=0)  # 等待时间(毫秒)
    timeout = Column(Integer, default=30)  # 超时时间(秒)
    
    # 创建时间
    created_at = Column(DateTime, default=func.now())
    
    # 关联任务
    task = relationship("Task", back_populates="steps")


class ExecutionLog(Base):
    """执行日志模型"""
    __tablename__ = "execution_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)
    
    # 日志信息
    level = Column(String, default="INFO")  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    
    # 步骤信息
    step_id = Column(Integer, nullable=True)
    step_name = Column(String, nullable=True)
    
    # 截图和错误信息
    screenshot_path = Column(String, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # 时间戳
    timestamp = Column(DateTime, default=func.now())


class BrowserSession(Base):
    """浏览器会话模型"""
    __tablename__ = "browser_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)
    
    # 会话信息
    session_id = Column(String, unique=True, index=True)
    browser_type = Column(String, default="chrome")  # chrome, firefox, edge
    
    # 配置信息
    window_size = Column(String, default="1920x1080")
    user_agent = Column(String, nullable=True)
    proxy_url = Column(String, nullable=True)
    
    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, default=func.now())


class UserSession(Base):
    """用户会话模型(用于可视化编辑器)"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    
    # 用户信息
    username = Column(String, nullable=True)
    is_anonymous = Column(Boolean, default=True)
    
    # 编辑器状态
    current_url = Column(String, nullable=True)
    current_task_id = Column(Integer, nullable=True)
    
    # 临时数据
    temp_data = Column(JSON, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, default=func.now())


# 关系定义
Task.steps = relationship("AutomationStep", back_populates="task", cascade="all, delete-orphan")