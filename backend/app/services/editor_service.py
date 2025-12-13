"""
可视化编辑器服务
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import json

from app.models.database import UserSession, Task, AutomationStep
from app.schemas import (
    EditorSessionCreate, 
    EditorSessionResponse, 
    RecordedStep,
    ActionType
)
from app.core.logging import logger


class EditorService:
    """可视化编辑器服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.temp_step_storage: Dict[str, List[Dict[str, Any]]] = {}
    
    async def create_session(self, session_data: EditorSessionCreate) -> EditorSessionResponse:
        """创建编辑器会话"""
        try:
            session_id = str(uuid.uuid4())
            
            session = UserSession(
                session_id=session_id,
                username=session_data.username,
                current_task_id=session_data.task_id,
                current_url=None,
                temp_data={}
            )
            
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
            logger.info(f"创建编辑器会话成功: {session_id}")
            
            return EditorSessionResponse(
                session_id=session.session_id,
                task_id=session.current_task_id,
                current_url=session.current_url,
                created_at=session.created_at,
                temp_data=session.temp_data
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建编辑器会话失败: {str(e)}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[EditorSessionResponse]:
        """获取编辑器会话"""
        try:
            session = self.db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()
            
            if not session:
                return None
            
            return EditorSessionResponse(
                session_id=session.session_id,
                task_id=session.current_task_id,
                current_url=session.current_url,
                created_at=session.created_at,
                temp_data=session.temp_data
            )
            
        except Exception as e:
            logger.error(f"获取编辑器会话失败: {str(e)}")
            raise
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """更新编辑器会话"""
        try:
            session = self.db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()
            
            if not session:
                return False
            
            # 更新字段
            for field, value in updates.items():
                if hasattr(session, field):
                    setattr(session, field, value)
            
            session.last_activity = datetime.now()
            self.db.commit()
            
            logger.info(f"更新编辑器会话成功: {session_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新编辑器会话失败: {str(e)}")
            return False
    
    async def close_session(self, session_id: str) -> bool:
        """关闭编辑器会话"""
        try:
            session = self.db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()
            
            if not session:
                return False
            
            self.db.delete(session)
            self.db.commit()
            
            # 清理临时数据
            if session_id in self.temp_step_storage:
                del self.temp_step_storage[session_id]
            
            logger.info(f"关闭编辑器会话成功: {session_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"关闭编辑器会话失败: {str(e)}")
            return False
    
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """获取活跃的编辑器会话"""
        try:
            # 获取最近活跃的会话（过去1小时内）
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            sessions = self.db.query(UserSession).filter(
                UserSession.last_activity >= one_hour_ago
            ).order_by(UserSession.last_activity.desc()).all()
            
            return [{
                "session_id": session.session_id,
                "username": session.username,
                "current_url": session.current_url,
                "current_task_id": session.current_task_id,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "is_anonymous": session.is_anonymous
            } for session in sessions]
            
        except Exception as e:
            logger.error(f"获取活跃会话失败: {str(e)}")
            raise
    
    async def get_recorded_steps(self, session_id: str) -> List[Dict[str, Any]]:
        """获取录制的步骤"""
        try:
            # 先从临时存储获取
            if session_id in self.temp_step_storage:
                return self.temp_step_storage[session_id]
            
            # 如果没有临时数据，尝试从数据库获取
            session = await self.get_session(session_id)
            if session and session.temp_data:
                return session.temp_data.get("recorded_steps", [])
            
            return []
            
        except Exception as e:
            logger.error(f"获取录制步骤失败: {str(e)}")
            return []
    
    async def save_recorded_steps(self, session_id: str, steps: List[RecordedStep]) -> Dict[str, Any]:
        """保存录制的步骤"""
        try:
            # 转换为字典格式
            step_dicts = [step.dict() for step in steps]
            
            # 保存到临时存储
            if session_id not in self.temp_step_storage:
                self.temp_step_storage[session_id] = []
            
            self.temp_step_storage[session_id].extend(step_dicts)
            
            # 同时保存到数据库
            session = self.db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()
            
            if session:
                if not session.temp_data:
                    session.temp_data = {}
                
                if "recorded_steps" not in session.temp_data:
                    session.temp_data["recorded_steps"] = []
                
                session.temp_data["recorded_steps"].extend(step_dicts)
                session.last_activity = datetime.now()
                self.db.commit()
            
            logger.info(f"保存录制步骤成功: {session_id}, 步骤数: {len(steps)}")
            
            return {
                "total_steps": len(self.temp_step_storage.get(session_id, [])),
                "saved_steps": len(steps)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存录制步骤失败: {str(e)}")
            raise
    
    async def convert_steps_to_automation(self, session_id: str, task_id: int) -> List[Dict[str, Any]]:
        """将录制的步骤转换为自动化步骤"""
        try:
            recorded_steps = await self.get_recorded_steps(session_id)
            
            automation_steps = []
            for i, step in enumerate(recorded_steps):
                automation_step = {
                    "task_id": task_id,
                    "step_name": f"步骤 {i+1}: {step['action_type']}",
                    "step_order": i,
                    "action_type": step['action_type'],
                    "target_selector": step.get('target_selector'),
                    "target_text": step.get('target_text'),
                    "target_url": step.get('target_url'),
                    "parameters": {
                        "x_path": step.get('x_path'),
                        "coordinates": step.get('coordinates'),
                        "wait_after": step.get('wait_after', 0)
                    },
                    "wait_time": step.get('wait_after', 0) * 1000,  # 转换为毫秒
                    "timeout": 30
                }
                automation_steps.append(automation_step)
            
            logger.info(f"转换步骤为自动化: {len(automation_steps)} 个步骤")
            return automation_steps
            
        except Exception as e:
            logger.error(f"转换步骤失败: {str(e)}")
            raise
    
    async def clear_recorded_steps(self, session_id: str) -> bool:
        """清除录制的步骤"""
        try:
            # 清除临时存储
            if session_id in self.temp_step_storage:
                self.temp_step_storage[session_id] = []
            
            # 清除数据库中的记录
            session = self.db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()
            
            if session and session.temp_data:
                session.temp_data["recorded_steps"] = []
                session.last_activity = datetime.now()
                self.db.commit()
            
            logger.info(f"清除录制步骤成功: {session_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"清除录制步骤失败: {str(e)}")
            return False
    
    async def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """获取会话分析数据"""
        try:
            session = await self.get_session(session_id)
            if not session:
                return {}
            
            recorded_steps = await self.get_recorded_steps(session_id)
            
            # 分析操作类型分布
            action_types = {}
            for step in recorded_steps:
                action_type = step['action_type']
                action_types[action_type] = action_types.get(action_type, 0) + 1
            
            # 分析时间分布
            if recorded_steps:
                timestamps = [step['timestamp'] for step in recorded_steps if 'timestamp' in step]
                duration = max(timestamps) - min(timestamps) if timestamps else 0
            else:
                duration = 0
            
            analytics = {
                "session_id": session_id,
                "total_steps": len(recorded_steps),
                "action_type_distribution": action_types,
                "session_duration": duration,
                "created_at": session.created_at,
                "last_activity": session.last_activity
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"获取会话分析失败: {str(e)}")
            return {}