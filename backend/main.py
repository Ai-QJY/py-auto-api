"""
py-auto-api 主应用
一个支持可视化编辑的网站自动化工具
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

from app.api.routes.tasks import router as tasks_router
from app.api.routes.automation import router as automation_router
from app.api.routes.editor import router as editor_router
from app.core.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    setup_logging()
    print("🚀 py-auto-api 服务启动")
    yield
    # 关闭时清理
    print("🛑 py-auto-api 服务关闭")


# 创建FastAPI应用
app = FastAPI(
    title="py-auto-api",
    description="支持可视化编辑的网站自动化工具",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(tasks_router, prefix="/api/v1", tags=["tasks"])
app.include_router(automation_router, prefix="/api/v1", tags=["automation"])
app.include_router(editor_router, prefix="/api/v1", tags=["editor"])

# 静态文件服务
app.mount("/static", StaticFiles(directory="../frontend"), name="static")
# 前端页面路由
from fastapi.responses import FileResponse
import os

@app.get("/")
async def serve_frontend():
    return FileResponse("../frontend/index.html")

@app.get("/editor")
async def serve_editor():
    return FileResponse("../frontend/index.html")

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.active_connections.remove(connection)

manager = ConnectionManager()

# WebSocket端点用于实时通信
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"收到消息: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )