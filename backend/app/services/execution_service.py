"""
任务执行服务
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any
import asyncio
import uuid
from datetime import datetime

from app.models.database import Task, AutomationStep, BrowserSession
from app.schemas import TaskStatus
from app.services.task_service import TaskService
from app.services.automation_service import AutomationService
from app.core.logging import logger


class ExecutionService:
    """任务执行服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_service = TaskService(db)
        self.automation_service = AutomationService(db)
        self.active_executions: Dict[str, Dict[str, Any]] = {}
    
    async def execute_task(self, task_id: int, execution_id: str):
        """执行单个任务"""
        try:
            # 记录执行开始
            self.active_executions[execution_id] = {
                "task_id": task_id,
                "status": "running",
                "start_time": datetime.now(),
                "current_step": 0,
                "total_steps": 0
            }
            
            logger.info(f"开始执行任务: {task_id} (执行ID: {execution_id})")
            
            # 更新任务状态
            await self.task_service.update_task_status(task_id, TaskStatus.RUNNING)
            
            # 获取任务步骤
            steps = self.db.query(AutomationStep).filter(
                AutomationStep.task_id == task_id
            ).order_by(AutomationStep.step_order).all()
            
            if not steps:
                await self.task_service.update_task_status(
                    task_id, TaskStatus.FAILED, "任务没有配置自动化步骤"
                )
                return
            
            # 创建浏览器会话
            browser_session = await self.automation_service.launch_browser(None)
            session_id = browser_session["session_id"]
            
            try:
                # 导航到目标URL
                task = await self.task_service.get_task(task_id)
                if task and task.url:
                    await self.automation_service.navigate_to_url(session_id, task.url)
                
                # 执行步骤
                success_count = 0
                failed_count = 0
                
                self.active_executions[execution_id]["total_steps"] = len(steps)
                
                for i, step in enumerate(steps):
                    self.active_executions[execution_id]["current_step"] = i + 1
                    
                    try:
                        # 检查任务是否被停止
                        current_task = await self.task_service.get_task(task_id)
                        if current_task.status == TaskStatus.CANCELLED:
                            logger.info(f"任务 {task_id} 被用户停止")
                            break
                        
                        # 执行步骤
                        result = await self.automation_service.execute_step(step, session_id)
                        success_count += 1
                        
                        logger.info(f"步骤执行成功: {step.step_name}")
                        
                    except Exception as step_error:
                        failed_count += 1
                        error_msg = f"步骤执行失败: {step.step_name}, 错误: {str(step_error)}"
                        logger.error(error_msg)
                        
                        # 记录错误但继续执行其他步骤
                        await self.automation_service._log_execution(
                            task_id, step.id, "ERROR", error_msg
                        )
                
                # 更新执行统计
                task.execution_count += 1
                task.success_count += success_count
                task.failure_count += failed_count
                
                # 决定最终状态
                if failed_count == 0:
                    final_status = TaskStatus.COMPLETED
                    error_message = None
                elif success_count > 0:
                    final_status = TaskStatus.COMPLETED  # 部分成功也算完成
                    error_message = f"部分步骤失败: {failed_count}/{len(steps)}"
                else:
                    final_status = TaskStatus.FAILED
                    error_message = "所有步骤执行失败"
                
                # 更新任务状态
                await self.task_service.update_task_status(task_id, final_status, error_message)
                
                logger.info(f"任务执行完成: {task_id}, 状态: {final_status}")
                
            finally:
                # 关闭浏览器会话
                await self.automation_service.close_session(session_id)
                
                # 清理执行记录
                if execution_id in self.active_executions:
                    del self.active_executions[execution_id]
            
        except Exception as e:
            error_msg = f"任务执行异常: {str(e)}"
            logger.error(error_msg)
            
            await self.task_service.update_task_status(task_id, TaskStatus.FAILED, error_msg)
            
            # 清理执行记录
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def batch_execute_tasks(self, task_ids: List[int], execution_id: str):
        """批量执行任务"""
        try:
            logger.info(f"开始批量执行任务: {task_ids} (执行ID: {execution_id})")
            
            # 记录批量执行开始
            self.active_executions[execution_id] = {
                "type": "batch",
                "task_ids": task_ids,
                "status": "running",
                "start_time": datetime.now(),
                "completed_tasks": 0,
                "failed_tasks": 0,
                "total_tasks": len(task_ids)
            }
            
            # 并发执行任务
            tasks = []
            for task_id in task_ids:
                task_execution_id = f"{execution_id}_task_{task_id}"
                task = asyncio.create_task(
                    self.execute_task(task_id, task_execution_id)
                )
                tasks.append(task)
            
            # 等待所有任务完成
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 更新批量执行状态
            batch_execution = self.active_executions[execution_id]
            batch_execution["status"] = "completed"
            batch_execution["completed_at"] = datetime.now()
            
            logger.info(f"批量执行完成: {execution_id}")
            
        except Exception as e:
            error_msg = f"批量执行异常: {str(e)}"
            logger.error(error_msg)
            
            # 更新执行状态
            if execution_id in self.active_executions:
                self.active_executions[execution_id]["status"] = "failed"
                self.active_executions[execution_id]["error"] = error_msg
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """获取执行状态"""
        return self.active_executions.get(execution_id, {})
    
    async def stop_execution(self, execution_id: str) -> bool:
        """停止执行"""
        try:
            if execution_id not in self.active_executions:
                return False
            
            execution = self.active_executions[execution_id]
            execution["status"] = "stopped"
            
            # 停止关联的任务
            if execution.get("type") == "batch":
                # 停止批量执行中的所有任务
                for task_id in execution.get("task_ids", []):
                    await self.task_service.stop_task(task_id)
            else:
                # 停止单个任务
                task_id = execution.get("task_id")
                if task_id:
                    await self.task_service.stop_task(task_id)
            
            logger.info(f"执行已停止: {execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"停止执行失败: {str(e)}")
            return False
    
    async def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取执行历史"""
        try:
            # 这里可以从数据库或日志中获取历史记录
            # 简化实现，返回当前活跃的执行记录
            history = []
            
            for execution_id, execution in self.active_executions.items():
                history.append({
                    "execution_id": execution_id,
                    **execution
                })
            
            return sorted(history, key=lambda x: x["start_time"], reverse=True)[:limit]
            
        except Exception as e:
            logger.error(f"获取执行历史失败: {str(e)}")
            return []