"""
浏览器录制器 - 处理可视化编辑器中的操作录制
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.models.database import UserSession, AutomationStep
from app.schemas import RecordedStep, ActionType
from app.core.logging import logger
from app.services.browser_manager import browser_manager


class BrowserRecorder:
    """浏览器录制器"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.active_recordings: Dict[str, Dict[str, Any]] = {}
    
    async def start_recording(self, session_id: str, target_url: str = None) -> Dict[str, Any]:
        """开始录制"""
        try:
            # 检查会话是否存在
            session = self.db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()
            
            if not session:
                raise ValueError(f"会话不存在: {session_id}")
            
            # 创建录制记录
            self.active_recordings[session_id] = {
                "start_time": datetime.now(),
                "target_url": target_url,
                "steps": [],
                "is_recording": True,
                "step_counter": 0
            }
            
            # 更新会话状态
            session.current_url = target_url
            self.db.commit()
            
            logger.info(f"开始录制: {session_id}")
            
            return {
                "session_id": session_id,
                "status": "recording_started",
                "start_time": datetime.now(),
                "target_url": target_url
            }
            
        except Exception as e:
            logger.error(f"开始录制失败: {str(e)}")
            raise
    
    async def stop_recording(self, session_id: str) -> Dict[str, Any]:
        """停止录制"""
        try:
            if session_id not in self.active_recordings:
                raise ValueError(f"录制不存在: {session_id}")
            
            recording = self.active_recordings[session_id]
            recording["is_recording"] = False
            recording["end_time"] = datetime.now()
            
            # 统计信息
            duration = (recording["end_time"] - recording["start_time"]).total_seconds()
            step_count = len(recording["steps"])
            
            logger.info(f"停止录制: {session_id}, 步骤数: {step_count}, 持续时间: {duration}秒")
            
            return {
                "session_id": session_id,
                "status": "recording_stopped",
                "duration": duration,
                "step_count": step_count,
                "steps": recording["steps"]
            }
            
        except Exception as e:
            logger.error(f"停止录制失败: {str(e)}")
            raise
    
    async def record_step(self, session_id: str, step_data: RecordedStep) -> bool:
        """记录单个步骤"""
        try:
            if session_id not in self.active_recordings:
                logger.warning(f"录制会话不存在: {session_id}")
                return False
            
            recording = self.active_recordings[session_id]
            
            if not recording["is_recording"]:
                logger.warning(f"录制已停止: {session_id}")
                return False
            
            # 添加步骤到录制
            step_dict = step_data.dict()
            step_dict["recorded_at"] = datetime.now().isoformat()
            step_dict["step_number"] = recording["step_counter"]
            
            recording["steps"].append(step_dict)
            recording["step_counter"] += 1
            
            logger.debug(f"记录步骤: {session_id}, 步骤: {step_data.action_type}")
            return True
            
        except Exception as e:
            logger.error(f"记录步骤失败: {str(e)}")
            return False
    
    async def save_recorded_steps(self, session_id: str, steps: List[RecordedStep]) -> Dict[str, Any]:
        """保存录制的步骤"""
        try:
            # 保存到临时存储
            step_dicts = [step.dict() for step in steps]
            
            # 更新会话的临时数据
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
                "total_steps": len(step_dicts),
                "saved_steps": len(steps),
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"保存录制步骤失败: {str(e)}")
            raise
    
    async def take_snapshot(self, session_id: str, url: str) -> Dict[str, Any]:
        """获取页面快照"""
        try:
            # 创建临时浏览器会话
            browser_session = await browser_manager.launch_browser(None)
            temp_session_id = browser_session["session_id"]
            
            try:
                # 导航到URL
                browser = await browser_manager.get_browser(temp_session_id)
                await browser.goto(url)
                
                # 等待页面加载
                await asyncio.sleep(3)
                
                # 获取截图
                screenshot = await browser.take_screenshot(full_page=True)
                
                # 获取页面信息
                page_info = await browser.get_page_info()
                
                # 转换为base64
                import base64
                screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
                
                return {
                    "session_id": session_id,
                    "url": url,
                    "screenshot_base64": screenshot_base64,
                    "page_title": page_info.get("title", ""),
                    "timestamp": datetime.now().isoformat(),
                    "page_info": page_info
                }
                
            finally:
                # 关闭临时会话
                await browser_manager.close_session(temp_session_id)
            
        except Exception as e:
            logger.error(f"获取页面快照失败: {str(e)}")
            raise
    
    async def validate_step_recording(self, step: RecordedStep) -> Dict[str, Any]:
        """验证录制的步骤"""
        try:
            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "suggestions": []
            }
            
            # 验证操作类型
            valid_actions = [action.value for action in ActionType]
            if step.action_type not in valid_actions:
                validation_result["errors"].append(f"不支持的操作类型: {step.action_type}")
                validation_result["is_valid"] = False
            
            # 验证选择器
            if step.target_selector:
                if not step.target_selector.strip():
                    validation_result["errors"].append("选择器不能为空")
                    validation_result["is_valid"] = False
                elif len(step.target_selector) > 500:
                    validation_result["warnings"].append("选择器较长，可能影响性能")
            
            # 验证输入文本
            if step.target_text:
                if len(step.target_text) > 10000:
                    validation_result["warnings"].append("输入文本较长，建议分段输入")
            
            # 验证坐标
            if step.coordinates:
                x, y = step.coordinates.get("x", 0), step.coordinates.get("y", 0)
                if x < 0 or y < 0:
                    validation_result["errors"].append("坐标不能为负数")
                    validation_result["is_valid"] = False
            
            # 验证时间戳
            if step.timestamp <= 0:
                validation_result["errors"].append("时间戳必须大于0")
                validation_result["is_valid"] = False
            
            # 添加建议
            if step.action_type == ActionType.CLICK and not step.target_selector:
                validation_result["suggestions"].append("点击操作建议使用选择器定位")
            
            if step.action_type == ActionType.TYPE and not step.target_selector:
                validation_result["suggestions"].append("输入操作建议使用选择器定位目标元素")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"验证录制步骤失败: {str(e)}")
            return {
                "is_valid": False,
                "errors": [f"验证过程出错: {str(e)}"]
            }
    
    async def optimize_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化录制步骤"""
        try:
            optimized_steps = []
            i = 0
            
            while i < len(steps):
                current_step = steps[i].copy()
                
                # 合并连续的等待步骤
                if current_step["action_type"] == ActionType.WAIT and i + 1 < len(steps):
                    next_step = steps[i + 1]
                    if next_step["action_type"] == ActionType.WAIT:
                        # 合并等待时间
                        current_wait = current_step.get("parameters", {}).get("wait_time", 0)
                        next_wait = next_step.get("parameters", {}).get("wait_time", 0)
                        current_step["parameters"] = current_step.get("parameters", {})
                        current_step["parameters"]["wait_time"] = current_wait + next_wait
                        i += 1  # 跳过下一个等待步骤
                
                # 移除冗余的滚动步骤
                if current_step["action_type"] == ActionType.SCROLL:
                    if optimized_steps and optimized_steps[-1]["action_type"] == ActionType.SCROLL:
                        # 合并滚动操作
                        prev_scroll = optimized_steps[-1]
                        current_scroll = current_step.get("parameters", {})
                        prev_scroll["parameters"] = prev_scroll.get("parameters", {})
                        prev_scroll["parameters"]["scroll_y"] = (
                            prev_scroll.get("parameters", {}).get("scroll_y", 0) +
                            current_scroll.get("scroll_y", 0)
                        )
                    else:
                        optimized_steps.append(current_step)
                else:
                    optimized_steps.append(current_step)
                
                i += 1
            
            logger.info(f"优化步骤: {len(steps)} -> {len(optimized_steps)}")
            return optimized_steps
            
        except Exception as e:
            logger.error(f"优化步骤失败: {str(e)}")
            return steps  # 返回原始步骤
    
    async def export_steps(self, session_id: str, format: str = "json") -> Dict[str, Any]:
        """导出录制的步骤"""
        try:
            # 从数据库获取录制步骤
            session = self.db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()
            
            if not session or not session.temp_data.get("recorded_steps"):
                raise ValueError(f"会话没有录制步骤: {session_id}")
            
            steps = session.temp_data["recorded_steps"]
            
            if format == "json":
                return {
                    "format": "json",
                    "session_id": session_id,
                    "export_time": datetime.now().isoformat(),
                    "step_count": len(steps),
                    "steps": steps
                }
            
            elif format == "automation":
                # 转换为自动化步骤格式
                automation_steps = []
                for i, step in enumerate(steps):
                    auto_step = {
                        "step_name": f"步骤 {i+1}",
                        "step_order": i,
                        "action_type": step["action_type"],
                        "target_selector": step.get("target_selector"),
                        "target_text": step.get("target_text"),
                        "target_url": step.get("target_url"),
                        "parameters": {
                            "recorded_data": step
                        },
                        "wait_time": step.get("wait_after", 0) * 1000,
                        "timeout": 30
                    }
                    automation_steps.append(auto_step)
                
                return {
                    "format": "automation",
                    "session_id": session_id,
                    "export_time": datetime.now().isoformat(),
                    "step_count": len(automation_steps),
                    "steps": automation_steps
                }
            
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
        except Exception as e:
            logger.error(f"导出步骤失败: {str(e)}")
            raise
    
    def get_active_recording_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取活跃录制信息"""
        return self.active_recordings.get(session_id)
    
    def get_all_active_recordings(self) -> Dict[str, Dict[str, Any]]:
        """获取所有活跃录制"""
        return {sid: info for sid, info in self.active_recordings.items() if info["is_recording"]}