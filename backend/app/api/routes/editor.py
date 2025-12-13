"""
可视化编辑器相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uuid
import json
import asyncio
import time

from app.core.database import get_db
from app.services.editor_service import EditorService
from app.services.browser_recorder import BrowserRecorder
from app.schemas import (
    EditorSessionCreate,
    EditorSessionResponse,
    RecordedStep,
    StepRecordingRequest,
    WebSocketMessage
)

router = APIRouter()

# WebSocket连接管理器
class EditorConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_info: Dict[str, Dict[str, Any]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_info[session_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "step_count": 0
        }

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_info:
            del self.session_info[session_id]

    async def send_message(self, session_id: str, message: Dict[str, Any]):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except Exception as e:
                self.disconnect(session_id)

    async def broadcast(self, message: Dict[str, Any], exclude_session: str = None):
        for session_id, connection in self.active_connections.items():
            if session_id != exclude_session:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    self.disconnect(session_id)

editor_manager = EditorConnectionManager()


@router.post("/editor/sessions", response_model=EditorSessionResponse)
async def create_editor_session(
    session_data: EditorSessionCreate,
    db: Session = Depends(get_db)
):
    """创建可视化编辑器会话"""
    try:
        editor_service = EditorService(db)
        session = await editor_service.create_session(session_data)
        return session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/editor/sessions/{session_id}", response_model=EditorSessionResponse)
async def get_editor_session(session_id: str, db: Session = Depends(get_db)):
    """获取编辑器会话信息"""
    try:
        editor_service = EditorService(db)
        session = await editor_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话未找到")
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/editor/sessions/{session_id}")
async def close_editor_session(session_id: str, db: Session = Depends(get_db)):
    """关闭编辑器会话"""
    try:
        editor_service = EditorService(db)
        success = await editor_service.close_session(session_id)
        
        # 清理WebSocket连接
        if session_id in editor_manager.active_connections:
            editor_manager.disconnect(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="会话未找到")
        return {"message": "会话关闭成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/editor/record-steps")
async def record_steps(request: StepRecordingRequest, db: Session = Depends(get_db)):
    """记录浏览器操作步骤"""
    try:
        editor_service = EditorService(db)
        browser_recorder = BrowserRecorder(db)
        
        # 保存录制的步骤
        result = await browser_recorder.save_recorded_steps(
            request.session_id,
            request.steps
        )
        
        # 通知相关WebSocket连接
        await editor_manager.send_message(request.session_id, {
            "type": "steps_recorded",
            "data": {
                "step_count": len(request.steps),
                "total_steps": result.get("total_steps", 0)
            }
        })
        
        return {
            "message": "步骤录制成功",
            "session_id": request.session_id,
            "recorded_steps": len(request.steps),
            "total_steps": result.get("total_steps", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/editor/recordings/{session_id}")
async def get_recorded_steps(session_id: str, db: Session = Depends(get_db)):
    """获取录制的步骤"""
    try:
        editor_service = EditorService(db)
        steps = await editor_service.get_recorded_steps(session_id)
        return steps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/editor/validate-selector")
async def validate_selector(request: dict):
    """验证选择器"""
    try:
        selector = request.get("selector")
        selector_type = request.get("type", "css")  # css, xpath, id, class
        page_url = request.get("page_url")
        
        if not selector:
            raise HTTPException(status_code=400, detail="缺少selector参数")
        
        validation_result = await validate_selector_syntax(selector, selector_type, page_url)
        
        return validation_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/editor/snapshot")
async def take_page_snapshot(request: dict, db: Session = Depends(get_db)):
    """获取页面快照"""
    try:
        session_id = request.get("session_id")
        url = request.get("url")
        
        if not session_id or not url:
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        browser_recorder = BrowserRecorder(db)
        snapshot = await browser_recorder.take_snapshot(session_id, url)
        
        return {
            "session_id": session_id,
            "url": url,
            "snapshot": snapshot,
            "timestamp": int(time.time())
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/editor/sessions")
async def get_active_sessions(db: Session = Depends(get_db)):
    """获取所有活跃的编辑器会话"""
    try:
        editor_service = EditorService(db)
        sessions = await editor_service.get_active_sessions()
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/editor/ws/{session_id}")
async def editor_websocket_endpoint(websocket: WebSocket, session_id: str):
    """编辑器WebSocket连接"""
    await editor_manager.connect(session_id, websocket)
    try:
        # 发送连接确认
        await editor_manager.send_message(session_id, {
            "type": "connected",
            "data": {"session_id": session_id}
        })
        
        # 发送当前会话状态
        await editor_manager.send_message(session_id, {
            "type": "session_status",
            "data": editor_manager.session_info.get(session_id, {})
        })
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理不同类型的消息
            await handle_websocket_message(session_id, message)
            
    except WebSocketDisconnect:
        editor_manager.disconnect(session_id)
    except Exception as e:
        editor_manager.disconnect(session_id)


# WebSocket消息处理
async def handle_websocket_message(session_id: str, message: Dict[str, Any]):
    """处理WebSocket消息"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == "ping":
        await editor_manager.send_message(session_id, {"type": "pong"})
    
    elif message_type == "update_status":
        # 更新会话状态
        if session_id in editor_manager.session_info:
            editor_manager.session_info[session_id].update(data)
    
    elif message_type == "request_snapshot":
        # 请求页面快照
        url = data.get("url")
        if url:
            await editor_manager.send_message(session_id, {
                "type": "snapshot_requested",
                "data": {"url": url}
            })
    
    elif message_type == "recording_event":
        # 处理录制事件
        event_type = data.get("event_type")
        if event_type == "start":
            if session_id in editor_manager.session_info:
                editor_manager.session_info[session_id]["recording"] = True
        elif event_type == "stop":
            if session_id in editor_manager.session_info:
                editor_manager.session_info[session_id]["recording"] = False


# 辅助函数
async def validate_selector_syntax(selector: str, selector_type: str, page_url: str = None):
    """验证选择器语法"""
    try:
        # 基本语法验证
        validation_results = {
            "selector": selector,
            "type": selector_type,
            "is_valid": False,
            "errors": [],
            "warnings": []
        }
        
        if selector_type == "css":
            # CSS选择器验证
            if not selector.strip():
                validation_results["errors"].append("CSS选择器不能为空")
            elif selector.startswith("//") or selector.startswith("./"):
                validation_results["warnings"].append("使用了XPath格式，但选择了CSS选择器类型")
            else:
                validation_results["is_valid"] = True
        
        elif selector_type == "xpath":
            # XPath验证
            if not selector.strip():
                validation_results["errors"].append("XPath不能为空")
            elif not (selector.startswith("//") or selector.startswith("./") or selector.startswith("/")):
                validation_results["warnings"].append("XPath建议以//或/开头")
            else:
                validation_results["is_valid"] = True
        
        elif selector_type == "id":
            # ID选择器验证
            if not selector.strip():
                validation_results["errors"].append("ID选择器不能为空")
            elif not selector.startswith("#"):
                validation_results["warnings"].append("ID选择器建议以#开头")
            else:
                validation_results["is_valid"] = True
        
        elif selector_type == "class":
            # 类选择器验证
            if not selector.strip():
                validation_results["errors"].append("类选择器不能为空")
            elif not selector.startswith("."):
                validation_results["warnings"].append("类选择器建议以.开头")
            else:
                validation_results["is_valid"] = True
        
        # 特殊情况检查
        if selector.strip().startswith("data-"):
            validation_results["suggestions"] = "这是一个data属性选择器，确保元素确实具有此属性"
        
        return validation_results
    
    except Exception as e:
        return {
            "selector": selector,
            "type": selector_type,
            "is_valid": False,
            "errors": [f"验证过程中出错: {str(e)}"]
        }