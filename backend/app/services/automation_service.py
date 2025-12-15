"""
自动化操作服务
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import json

from app.models.database import AutomationStep, Task, BrowserSession, ExecutionLog
from app.schemas import (
    AutomationStepCreate, 
    AutomationStepResponse,
    AutomationStepUpdate,
    BrowserConfig,
    ActionType
)
from app.core.logging import logger
from app.services.browser_manager import BrowserManager


class AutomationService:
    """自动化操作服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.browser_manager = BrowserManager()
    
    async def create_step(self, step_data: AutomationStepCreate) -> AutomationStepResponse:
        """创建自动化步骤"""
        try:
            # 验证步骤顺序
            existing_steps = self.db.query(AutomationStep).filter(
                AutomationStep.task_id == step_data.task_id
            ).count()
            
            if step_data.step_order < 0:
                step_data.step_order = existing_steps
            
            step = AutomationStep(
                task_id=step_data.task_id,
                step_name=step_data.step_name,
                step_order=step_data.step_order,
                action_type=step_data.action_type,
                target_selector=step_data.target_selector,
                target_text=step_data.target_text,
                target_url=step_data.target_url,
                parameters=step_data.parameters,
                wait_time=step_data.wait_time,
                timeout=step_data.timeout
            )
            
            self.db.add(step)
            self.db.commit()
            self.db.refresh(step)
            
            logger.info(f"创建自动化步骤成功: {step.step_name} (ID: {step.id})")
            return AutomationStepResponse.from_orm(step)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建自动化步骤失败: {str(e)}")
            raise
    
    async def get_steps_by_task(self, task_id: int) -> List[AutomationStepResponse]:
        """获取任务的自动化步骤"""
        try:
            steps = self.db.query(AutomationStep).filter(
                AutomationStep.task_id == task_id
            ).order_by(AutomationStep.step_order).all()
            
            return [AutomationStepResponse.from_orm(step) for step in steps]
            
        except Exception as e:
            logger.error(f"获取任务步骤失败 (Task ID: {task_id}): {str(e)}")
            raise
    
    async def update_step(self, step_id: int, step_data: dict) -> Optional[AutomationStepResponse]:
        """更新自动化步骤"""
        try:
            step = self.db.query(AutomationStep).filter(AutomationStep.id == step_id).first()
            if not step:
                return None
            
            # 更新字段
            for field, value in step_data.items():
                if hasattr(step, field):
                    setattr(step, field, value)
            
            self.db.commit()
            self.db.refresh(step)
            
            logger.info(f"更新自动化步骤成功: {step.step_name} (ID: {step.id})")
            return AutomationStepResponse.from_orm(step)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新自动化步骤失败 (ID: {step_id}): {str(e)}")
            raise
    
    async def delete_step(self, step_id: int) -> bool:
        """删除自动化步骤"""
        try:
            step = self.db.query(AutomationStep).filter(AutomationStep.id == step_id).first()
            if not step:
                return False
            
            self.db.delete(step)
            self.db.commit()
            
            logger.info(f"删除自动化步骤成功: {step_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除自动化步骤失败 (ID: {step_id}): {str(e)}")
            raise
    
    async def execute_step(self, step: AutomationStep, session_id: str) -> Dict[str, Any]:
        """执行单个自动化步骤"""
        try:
            # 记录开始执行
            await self._log_execution(step.task_id, step.id, "INFO", f"开始执行步骤: {step.step_name}")
            
            # 根据操作类型执行相应操作
            if step.action_type == ActionType.CLICK:
                result = await self._execute_click(step, session_id)
            elif step.action_type == ActionType.TYPE:
                result = await self._execute_type(step, session_id)
            elif step.action_type == ActionType.SCROLL:
                result = await self._execute_scroll(step, session_id)
            elif step.action_type == ActionType.WAIT:
                result = await self._execute_wait(step, session_id)
            elif step.action_type == ActionType.NAVIGATE:
                result = await self._execute_navigate(step, session_id)
            elif step.action_type == ActionType.SCREENSHOT:
                result = await self._execute_screenshot(step, session_id)
            else:
                raise ValueError(f"不支持的操作类型: {step.action_type}")
            
            # 记录成功执行
            await self._log_execution(step.task_id, step.id, "INFO", 
                                    f"步骤执行成功: {step.step_name}", result)
            
            # 等待指定时间
            if step.wait_time > 0:
                await asyncio.sleep(step.wait_time / 1000)
            
            return result
            
        except Exception as e:
            error_msg = f"步骤执行失败: {step.step_name}, 错误: {str(e)}"
            await self._log_execution(step.task_id, step.id, "ERROR", error_msg)
            logger.error(error_msg)
            raise
    
    async def _execute_click(self, step: AutomationStep, session_id: str) -> Dict[str, Any]:
        """执行点击操作"""
        browser = await self.browser_manager.get_browser(session_id)
        
        if not step.target_selector:
            raise ValueError("点击操作需要指定目标选择器")
        
        element = await browser.find_element(step.target_selector)
        await element.click()
        
        return {
            "action": "click",
            "selector": step.target_selector,
            "success": True
        }
    
    async def _execute_type(self, step: AutomationStep, session_id: str) -> Dict[str, Any]:
        """执行输入操作"""
        browser = await self.browser_manager.get_browser(session_id)
        
        if not step.target_selector:
            raise ValueError("输入操作需要指定目标选择器")
        
        if not step.target_text:
            raise ValueError("输入操作需要指定输入文本")
        
        element = await browser.find_element(step.target_selector)
        await element.fill(step.target_text)
        
        return {
            "action": "type",
            "selector": step.target_selector,
            "text": step.target_text,
            "success": True
        }
    
    async def _execute_scroll(self, step: AutomationStep, session_id: str) -> Dict[str, Any]:
        """执行滚动操作"""
        browser = await self.browser_manager.get_browser(session_id)
        
        await browser.page.evaluate("window.scrollBy(0, window.innerHeight)")
        
        return {
            "action": "scroll",
            "direction": "down",
            "success": True
        }
    
    async def _execute_wait(self, step: AutomationStep, session_id: str) -> Dict[str, Any]:
        """执行等待操作"""
        wait_time = step.parameters.get("wait_time", step.timeout) if step.parameters else step.timeout
        
        await asyncio.sleep(wait_time)
        
        return {
            "action": "wait",
            "duration": wait_time,
            "success": True
        }
    
    async def _execute_navigate(self, step: AutomationStep, session_id: str) -> Dict[str, Any]:
        """执行导航操作"""
        browser = await self.browser_manager.get_browser(session_id)
        
        if not step.target_url:
            raise ValueError("导航操作需要指定URL")
        
        await browser.goto(step.target_url)
        
        return {
            "action": "navigate",
            "url": step.target_url,
            "success": True
        }
    
    async def _execute_screenshot(self, step: AutomationStep, session_id: str) -> Dict[str, Any]:
        """执行截图操作"""
        browser = await self.browser_manager.get_browser(session_id)
        
        screenshot_data = await browser.take_screenshot()
        
        return {
            "action": "screenshot",
            "success": True,
            "screenshot_size": len(screenshot_data)
        }
    
    async def preview_automation(self, task_id: int, preview_id: str):
        """预览自动化操作"""
        try:
            # 获取任务和步骤
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError(f"任务未找到: {task_id}")
            
            steps = self.db.query(AutomationStep).filter(
                AutomationStep.task_id == task_id
            ).order_by(AutomationStep.step_order).all()
            
            # 创建临时浏览器会话
            config = BrowserConfig()
            session_info = await self.browser_manager.launch_browser(config)
            session_id = session_info["session_id"]
            
            # 执行预览
            preview_result = {
                "preview_id": preview_id,
                "task_id": task_id,
                "total_steps": len(steps),
                "executed_steps": 0,
                "results": []
            }
            
            try:
                # 导航到目标URL
                if task.url:
                    browser = await self.browser_manager.get_browser(session_id)
                    await browser.goto(task.url)
                
                # 执行步骤预览
                for step in steps:
                    try:
                        result = await self.execute_step(step, session_id)
                        preview_result["results"].append({
                            "step_id": step.id,
                            "step_name": step.step_name,
                            "success": True,
                            "result": result
                        })
                        preview_result["executed_steps"] += 1
                        
                        # 短暂延迟以便观察
                        await asyncio.sleep(2)
                        
                    except Exception as step_error:
                        preview_result["results"].append({
                            "step_id": step.id,
                            "step_name": step.step_name,
                            "success": False,
                            "error": str(step_error)
                        })
                        break  # 预览时遇到错误就停止
                
                logger.info(f"自动化预览完成: {preview_id}")
                
            finally:
                # 关闭临时会话
                await self.browser_manager.close_session(session_id)
            
            return preview_result
            
        except Exception as e:
            logger.error(f"自动化预览失败: {str(e)}")
            raise
    
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """获取活跃的浏览器会话"""
        try:
            sessions = self.db.query(BrowserSession).filter(
                BrowserSession.is_active == True
            ).all()
            
            return [{
                "session_id": session.session_id,
                "task_id": session.task_id,
                "browser_type": session.browser_type,
                "window_size": session.window_size,
                "created_at": session.created_at,
                "last_activity": session.last_activity
            } for session in sessions]
            
        except Exception as e:
            logger.error(f"获取活跃会话失败: {str(e)}")
            raise
    
    async def close_session(self, session_id: str) -> bool:
        """关闭浏览器会话"""
        try:
            # 关闭浏览器
            success = await self.browser_manager.close_session(session_id)
            
            if success:
                # 更新数据库
                session = self.db.query(BrowserSession).filter(
                    BrowserSession.session_id == session_id
                ).first()
                
                if session:
                    session.is_active = False
                    self.db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"关闭会话失败: {str(e)}")
            return False
    
    async def launch_browser(self, config: BrowserConfig) -> Dict[str, Any]:
        """启动浏览器会话"""
        try:
            session_info = await self.browser_manager.launch_browser(config)
            
            # 保存会话信息到数据库
            browser_session = BrowserSession(
                session_id=session_info["session_id"],
                task_id=None,  # 临时会话，暂无任务关联
                browser_type=config.browser_type,
                window_size=config.window_size,
                user_agent=config.user_agent,
                proxy_url=config.proxy_url
            )
            
            self.db.add(browser_session)
            self.db.commit()
            
            return session_info
            
        except Exception as e:
            logger.error(f"启动浏览器失败: {str(e)}")
            raise
    
    async def navigate_to_url(self, session_id: str, url: str) -> Dict[str, Any]:
        """浏览器导航到指定URL"""
        try:
            browser = await self.browser_manager.get_browser(session_id)
            await browser.goto(url)
            
            # 更新会话活动
            session = self.db.query(BrowserSession).filter(
                BrowserSession.session_id == session_id
            ).first()
            if session:
                session.last_activity = datetime.now()
                self.db.commit()
            
            return {
                "url": url,
                "title": await browser.title(),
                "final_url": browser.url
            }
            
        except Exception as e:
            logger.error(f"浏览器导航失败: {str(e)}")
            raise
    
    async def take_screenshot(self, session_id: str) -> str:
        """获取浏览器截图"""
        try:
            browser = await self.browser_manager.get_browser(session_id)
            screenshot_data = await browser.take_screenshot()
            
            # 转换为base64
            import base64
            return base64.b64encode(screenshot_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"获取截图失败: {str(e)}")
            raise
    
    async def _log_execution(self, task_id: int, step_id: int, level: str, message: str, details: Dict[str, Any] = None):
        """记录执行日志"""
        try:
            log = ExecutionLog(
                task_id=task_id,
                level=level,
                message=message,
                step_id=step_id,
                error_details=details
            )
            
            self.db.add(log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"记录执行日志失败: {str(e)}")