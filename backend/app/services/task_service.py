"""
任务管理服务
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.models.database import Task, AutomationStep, ExecutionLog
from app.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskStatus
from app.core.logging import logger


class TaskService:
    """任务管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """创建新任务"""
        try:
            task = Task(
                name=task_data.name,
                description=task_data.description,
                url=task_data.url,
                priority=task_data.priority,
                parameters=task_data.parameters
            )
            
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"创建任务成功: {task.name} (ID: {task.id})")
            return TaskResponse.from_orm(task)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建任务失败: {str(e)}")
            raise
    
    async def get_task(self, task_id: int) -> Optional[TaskResponse]:
        """获取任务详情"""
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            return TaskResponse.from_orm(task) if task else None
            
        except Exception as e:
            logger.error(f"获取任务失败 (ID: {task_id}): {str(e)}")
            raise
    
    async def get_tasks(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        status: Optional[TaskStatus] = None
    ) -> List[TaskResponse]:
        """获取任务列表"""
        try:
            query = self.db.query(Task)
            
            if status:
                query = query.filter(Task.status == status)
            
            tasks = query.order_by(desc(Task.created_at)).offset(skip).limit(limit).all()
            return [TaskResponse.from_orm(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            raise
    
    async def update_task(self, task_id: int, task_data: TaskUpdate) -> Optional[TaskResponse]:
        """更新任务"""
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None
            
            # 更新字段
            update_data = task_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(task, field, value)
            
            task.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"更新任务成功: {task.name} (ID: {task.id})")
            return TaskResponse.from_orm(task)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新任务失败 (ID: {task_id}): {str(e)}")
            raise
    
    async def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            
            self.db.delete(task)
            self.db.commit()
            
            logger.info(f"删除任务成功: {task_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除任务失败 (ID: {task_id}): {str(e)}")
            raise
    
    async def initialize_task(self, task_id: int):
        """初始化任务"""
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"初始化任务失败，未找到任务: {task_id}")
                return
            
            # 验证任务配置
            if not task.url:
                await self.update_task_status(task_id, TaskStatus.FAILED, "缺少目标URL")
                return
            
            # 检查是否有自动化步骤
            steps_count = self.db.query(AutomationStep).filter(
                AutomationStep.task_id == task_id
            ).count()
            
            if steps_count == 0:
                logger.warning(f"任务 {task_id} 没有配置自动化步骤")
            
            logger.info(f"任务初始化完成: {task_id}")
            
        except Exception as e:
            logger.error(f"初始化任务失败 (ID: {task_id}): {str(e)}")
            await self.update_task_status(task_id, TaskStatus.FAILED, str(e))
    
    async def update_task_status(self, task_id: int, status: TaskStatus, error_message: str = None):
        """更新任务状态"""
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return
            
            old_status = task.status
            task.status = status
            task.updated_at = datetime.now()
            
            # 设置时间戳
            if status == TaskStatus.RUNNING and old_status != TaskStatus.RUNNING:
                task.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now()
            
            # 设置错误信息
            if error_message:
                task.error_message = error_message
            
            self.db.commit()
            
            logger.info(f"任务状态更新: {task_id} {old_status} -> {status}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新任务状态失败 (ID: {task_id}): {str(e)}")
    
    async def calculate_progress(self, task_id: int) -> float:
        """计算任务进度"""
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return 0.0
            
            if task.status == TaskStatus.PENDING:
                return 0.0
            elif task.status == TaskStatus.COMPLETED:
                return 100.0
            elif task.status == TaskStatus.FAILED:
                return 0.0
            
            # 计算基于步骤的进度
            total_steps = self.db.query(AutomationStep).filter(
                AutomationStep.task_id == task_id
            ).count()
            
            if total_steps == 0:
                return 0.0
            
            # 这里可以根据执行日志来计算实际进度
            # 简化实现，返回估计值
            if task.started_at:
                elapsed_time = (datetime.now() - task.started_at).total_seconds()
                estimated_total = 30 * total_steps  # 假设每步平均30秒
                progress = min((elapsed_time / estimated_total) * 100, 90.0)
                return progress
            
            return 0.0
            
        except Exception as e:
            logger.error(f"计算任务进度失败 (ID: {task_id}): {str(e)}")
            return 0.0
    
    async def get_current_step(self, task_id: int) -> Optional[str]:
        """获取当前执行步骤"""
        try:
            # 这里可以根据执行日志来获取当前步骤
            # 简化实现
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task or task.status != TaskStatus.RUNNING:
                return None
            
            # 获取下一个要执行的步骤
            next_step = self.db.query(AutomationStep).filter(
                and_(
                    AutomationStep.task_id == task_id,
                    AutomationStep.step_order >= 0
                )
            ).order_by(AutomationStep.step_order).first()
            
            return next_step.step_name if next_step else "准备执行"
            
        except Exception as e:
            logger.error(f"获取当前步骤失败 (ID: {task_id}): {str(e)}")
            return None
    
    async def get_estimated_completion(self, task_id: int) -> Optional[datetime]:
        """获取预计完成时间"""
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task or task.status != TaskStatus.RUNNING or not task.started_at:
                return None
            
            # 计算剩余时间
            progress = await self.calculate_progress(task_id)
            if progress <= 0:
                return None
            
            elapsed_time = (datetime.now() - task.started_at).total_seconds()
            estimated_total_time = elapsed_time / (progress / 100)
            remaining_time = estimated_total_time - elapsed_time
            
            return datetime.now() + timedelta(seconds=remaining_time)
            
        except Exception as e:
            logger.error(f"计算预计完成时间失败 (ID: {task_id}): {str(e)}")
            return None
    
    async def get_overview_stats(self) -> dict:
        """获取任务概览统计"""
        try:
            # 统计各状态任务数量
            status_counts = self.db.query(
                Task.status,
                func.count(Task.id).label('count')
            ).group_by(Task.status).all()
            
            total_tasks = self.db.query(func.count(Task.id)).scalar()
            
            # 最近任务统计
            recent_tasks = self.db.query(Task).filter(
                Task.created_at >= datetime.now() - timedelta(days=7)
            ).count()
            
            # 成功率统计
            completed_tasks = self.db.query(Task).filter(Task.status == TaskStatus.COMPLETED).count()
            success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            stats = {
                "total_tasks": total_tasks,
                "status_breakdown": {status: count for status, count in status_counts},
                "recent_tasks_7days": recent_tasks,
                "success_rate": round(success_rate, 2),
                "active_tasks": sum(count for status, count in status_counts 
                                  if status in [TaskStatus.PENDING, TaskStatus.RUNNING])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取概览统计失败: {str(e)}")
            raise
    
    async def stop_task(self, task_id: int) -> bool:
        """停止任务执行"""
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            
            if task.status not in [TaskStatus.RUNNING, TaskStatus.PENDING]:
                return False
            
            await self.update_task_status(task_id, TaskStatus.CANCELLED, "用户手动停止")
            
            # 这里可以添加停止浏览器会话的逻辑
            
            return True
            
        except Exception as e:
            logger.error(f"停止任务失败 (ID: {task_id}): {str(e)}")
            return False