"""
自动化相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import time

from app.core.database import get_db
from app.services.automation_service import AutomationService
from app.schemas import (
    AutomationStepCreate, 
    AutomationStepResponse, 
    BrowserConfig,
    ExecutionRequest,
    ExecutionResponse
)

router = APIRouter()


@router.post("/automation/steps", response_model=AutomationStepResponse)
async def create_automation_step(
    step_data: AutomationStepCreate,
    db: Session = Depends(get_db)
):
    """创建自动化步骤"""
    try:
        automation_service = AutomationService(db)
        step = await automation_service.create_step(step_data)
        return step
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/automation/steps/task/{task_id}", response_model=List[AutomationStepResponse])
async def get_task_steps(task_id: int, db: Session = Depends(get_db)):
    """获取任务的自动化步骤"""
    try:
        automation_service = AutomationService(db)
        steps = await automation_service.get_steps_by_task(task_id)
        return steps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/automation/steps/{step_id}", response_model=AutomationStepResponse)
async def update_automation_step(
    step_id: int,
    step_data: dict,  # 使用dict避免循环导入
    db: Session = Depends(get_db)
):
    """更新自动化步骤"""
    try:
        automation_service = AutomationService(db)
        step = await automation_service.update_step(step_id, step_data)
        if not step:
            raise HTTPException(status_code=404, detail="步骤未找到")
        return step
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/automation/steps/{step_id}")
async def delete_automation_step(step_id: int, db: Session = Depends(get_db)):
    """删除自动化步骤"""
    try:
        automation_service = AutomationService(db)
        success = await automation_service.delete_step(step_id)
        if not success:
            raise HTTPException(status_code=404, detail="步骤未找到")
        return {"message": "步骤删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/preview")
async def preview_automation(
    request: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """预览自动化操作"""
    try:
        task_id = request.get("task_id")
        if not task_id:
            raise HTTPException(status_code=400, detail="缺少task_id参数")
        
        automation_service = AutomationService(db)
        
        preview_id = f"preview_{task_id}_{int(time.time())}"
        background_tasks.add_task(
            automation_service.preview_automation,
            task_id,
            preview_id
        )
        
        return {
            "message": "预览开始",
            "preview_id": preview_id,
            "task_id": task_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/sessions")
async def get_active_sessions(db: Session = Depends(get_db)):
    """获取活跃的浏览器会话"""
    try:
        automation_service = AutomationService(db)
        sessions = await automation_service.get_active_sessions()
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/automation/sessions/{session_id}")
async def close_browser_session(session_id: str, db: Session = Depends(get_db)):
    """关闭浏览器会话"""
    try:
        automation_service = AutomationService(db)
        success = await automation_service.close_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="会话未找到")
        return {"message": "会话关闭成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/browser/launch")
async def launch_browser(
    config: BrowserConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """启动浏览器会话"""
    try:
        automation_service = AutomationService(db)
        
        session_info = await automation_service.launch_browser(config)
        
        return {
            "session_id": session_info["session_id"],
            "status": "launched",
            "browser_type": config.browser_type,
            "control_url": session_info["control_url"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/browser/{session_id}/navigate")
async def browser_navigate(
    session_id: str,
    request: dict,
    db: Session = Depends(get_db)
):
    """浏览器导航到指定URL"""
    try:
        url = request.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="缺少url参数")
        
        automation_service = AutomationService(db)
        result = await automation_service.navigate_to_url(session_id, url)
        
        return {
            "session_id": session_id,
            "url": url,
            "status": "navigated",
            "title": result.get("title"),
            "final_url": result.get("final_url")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/browser/{session_id}/screenshot")
async def take_screenshot(
    session_id: str,
    db: Session = Depends(get_db)
):
    """获取浏览器截图"""
    try:
        automation_service = AutomationService(db)
        screenshot_data = await automation_service.take_screenshot(session_id)
        
        return {
            "session_id": session_id,
            "screenshot_base64": screenshot_data,
            "timestamp": int(time.time())
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/validate/xpath")
async def validate_xpath(request: dict):
    """验证XPath选择器"""
    try:
        xpath = request.get("xpath")
        if not xpath:
            raise HTTPException(status_code=400, detail="缺少xpath参数")
        
        # 基本XPath语法验证
        is_valid = await validate_xpath_syntax(xpath)
        
        return {
            "xpath": xpath,
            "is_valid": is_valid,
            "estimated_elements": "多个" if "//" in xpath else "单个"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 辅助函数
async def validate_xpath_syntax(xpath: str) -> bool:
    """验证XPath语法基本正确性"""
    try:
        import re
        
        # 基本XPath模式检查
        patterns = [
            r'^//.*',  # 以//开头
            r'^\..*',  # 以.开头
            r'^/.*',   # 以/开头
            r'.*\[[0-9]+\]',  # 包含索引
            r'.*\[@.*\]',  # 包含属性选择
        ]
        
        for pattern in patterns:
            if re.match(pattern, xpath):
                return True
        
        return False
    except:
        return False