"""
任务管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.database import Task
from app.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskStatus
from app.services.task_service import TaskService
from app.services.execution_service import ExecutionService

router = APIRouter()


@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """创建新任务"""
    try:
        task_service = TaskService(db)
        task = await task_service.create_task(task_data)
        
        # 后台初始化任务
        background_tasks.add_task(task_service.initialize_task, task.id)
        
        return task
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[TaskStatus] = None,
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    try:
        task_service = TaskService(db)
        tasks = await task_service.get_tasks(
            skip=skip,
            limit=limit,
            status=status
        )
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取特定任务"""
    try:
        task_service = TaskService(db)
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务未找到")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db)
):
    """更新任务"""
    try:
        task_service = TaskService(db)
        task = await task_service.update_task(task_id, task_data)
        if not task:
            raise HTTPException(status_code=404, detail="任务未找到")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务"""
    try:
        task_service = TaskService(db)
        success = await task_service.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="任务未找到")
        return {"message": "任务删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """执行任务"""
    try:
        task_service = TaskService(db)
        execution_service = ExecutionService(db)
        
        # 检查任务状态
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务未找到")
        
        if task.status in ["running"]:
            raise HTTPException(status_code=400, detail="任务正在执行中")
        
        # 后台执行任务
        execution_id = f"exec_{task_id}_{int(datetime.now().timestamp())}"
        background_tasks.add_task(
            execution_service.execute_task,
            task_id,
            execution_id
        )
        
        return {
            "message": "任务开始执行",
            "execution_id": execution_id,
            "task_id": task_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/batch/execute", response_model=dict)
async def batch_execute_tasks(
    request: dict,  # 使用dict避免循环导入
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """批量执行任务"""
    try:
        task_ids = request.get("task_ids", [])
        if not task_ids:
            raise HTTPException(status_code=400, detail="任务ID列表不能为空")
        
        execution_service = ExecutionService(db)
        
        execution_id = f"batch_{int(datetime.now().timestamp())}"
        background_tasks.add_task(
            execution_service.batch_execute_tasks,
            task_ids,
            execution_id
        )
        
        return {
            "message": "批量任务开始执行",
            "execution_id": execution_id,
            "task_count": len(task_ids)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: int, db: Session = Depends(get_db)):
    """获取任务执行状态"""
    try:
        task_service = TaskService(db)
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务未找到")
        
        return {
            "task_id": task_id,
            "status": task.status,
            "progress": await task_service.calculate_progress(task_id),
            "current_step": await task_service.get_current_step(task_id),
            "started_at": task.started_at,
            "estimated_completion": await task_service.get_estimated_completion(task_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/stats/overview")
async def get_tasks_stats(db: Session = Depends(get_db)):
    """获取任务统计信息"""
    try:
        task_service = TaskService(db)
        stats = await task_service.get_overview_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/stop")
async def stop_task(task_id: int, db: Session = Depends(get_db)):
    """停止任务执行"""
    try:
        task_service = TaskService(db)
        success = await task_service.stop_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="任务未找到或无法停止")
        return {"message": "任务停止成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))