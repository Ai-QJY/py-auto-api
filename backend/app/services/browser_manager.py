"""
浏览器管理器 - 使用Playwright进行浏览器自动化
"""

import asyncio
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from app.core.config import settings
from app.core.logging import logger
import json


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self):
        self.active_browsers: Dict[str, Dict[str, Any]] = {}
        self.playwright = None
    
    async def initialize(self):
        """初始化Playwright"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            logger.info("Playwright 初始化完成")
    
    async def launch_browser(self, config: Any) -> Dict[str, Any]:
        """启动新的浏览器会话"""
        try:
            await self.initialize()
            
            # 默认配置
            browser_config = {
                "browser_type": "chromium",
                "headless": settings.BROWSER_HEADLESS,
                "window_size": "1920x1080",
                "user_agent": None,
                "proxy_url": None
            }
            
            # 如果提供了自定义配置，更新默认配置
            if config:
                for key, value in config.dict().items():
                    if value is not None:
                        browser_config[key] = value
            
            # 启动浏览器
            browser = await self.playwright.chromium.launch(
                headless=browser_config["headless"],
                args=['--no-sandbox', '--disable-setuid-sandbox'] if browser_config["headless"] else []
            )
            
            # 创建浏览器上下文
            context_options = {
                "viewport": {
                    "width": int(browser_config["window_size"].split("x")[0]),
                    "height": int(browser_config["window_size"].split("x")[1])
                }
            }
            
            if browser_config["user_agent"]:
                context_options["user_agent"] = browser_config["user_agent"]
            
            if browser_config["proxy_url"]:
                context_options["proxy"] = {"server": browser_config["proxy_url"]}
            
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            
            # 生成会话ID
            import uuid
            session_id = str(uuid.uuid4())
            
            # 保存会话信息
            self.active_browsers[session_id] = {
                "browser": browser,
                "context": context,
                "page": page,
                "config": browser_config,
                "created_at": asyncio.get_event_loop().time()
            }
            
            logger.info(f"启动浏览器会话: {session_id}")
            
            return {
                "session_id": session_id,
                "browser_type": browser_config["browser_type"],
                "control_url": f"ws://localhost:8000/ws/{session_id}"  # WebSocket控制地址
            }
            
        except Exception as e:
            logger.error(f"启动浏览器失败: {str(e)}")
            raise
    
    async def get_browser(self, session_id: str) -> Optional["BrowserWrapper"]:
        """获取浏览器会话"""
        if session_id not in self.active_browsers:
            return None
        
        session = self.active_browsers[session_id]
        return BrowserWrapper(session_id, session["browser"], session["context"], session["page"])
    
    async def close_session(self, session_id: str) -> bool:
        """关闭浏览器会话"""
        try:
            if session_id not in self.active_browsers:
                return False
            
            session = self.active_browsers[session_id]
            
            # 关闭页面
            if "page" in session:
                await session["page"].close()
            
            # 关闭上下文
            if "context" in session:
                await session["context"].close()
            
            # 关闭浏览器
            if "browser" in session:
                await session["browser"].close()
            
            # 从活跃会话中移除
            del self.active_browsers[session_id]
            
            logger.info(f"关闭浏览器会话: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"关闭浏览器会话失败: {session_id}, 错误: {str(e)}")
            return False
    
    async def close_all_sessions(self):
        """关闭所有浏览器会话"""
        session_ids = list(self.active_browsers.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
        
        # 关闭Playwright
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        logger.info("所有浏览器会话已关闭")


class BrowserWrapper:
    """浏览器操作封装器"""
    
    def __init__(self, session_id: str, browser: Browser, context: BrowserContext, page: Page):
        self.session_id = session_id
        self.browser = browser
        self.context = context
        self.page = page
        self.url = ""
        self.title = ""
    
    async def goto(self, url: str):
        """导航到指定URL"""
        try:
            response = await self.page.goto(url, timeout=settings.BROWSER_TIMEOUT * 1000)
            self.url = self.page.url
            self.title = await self.page.title()
            
            logger.info(f"浏览器导航: {self.session_id} -> {url}")
            return response
            
        except Exception as e:
            logger.error(f"浏览器导航失败: {self.session_id} -> {url}, 错误: {str(e)}")
            raise
    
    async def find_element(self, selector: str, timeout: int = 30):
        """查找页面元素"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            return element
        except Exception as e:
            logger.error(f"查找元素失败: {selector}, 错误: {str(e)}")
            raise
    
    async def click(self, selector: str, timeout: int = 30):
        """点击元素"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            await element.click()
            logger.info(f"点击元素: {selector}")
        except Exception as e:
            logger.error(f"点击元素失败: {selector}, 错误: {str(e)}")
            raise
    
    async def fill(self, selector: str, text: str, timeout: int = 30):
        """输入文本"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            await element.fill(text)
            logger.info(f"输入文本: {selector} = {text}")
        except Exception as e:
            logger.error(f"输入文本失败: {selector}, 错误: {str(e)}")
            raise
    
    async def type_text(self, text: str):
        """输入文本到当前焦点元素"""
        try:
            await self.page.type(text)
        except Exception as e:
            logger.error(f"键盘输入失败: {str(e)}")
            raise
    
    async def scroll(self, x: int = 0, y: int = 0):
        """滚动页面"""
        try:
            await self.page.evaluate(f"window.scrollBy({x}, {y})")
        except Exception as e:
            logger.error(f"滚动页面失败: {str(e)}")
            raise
    
    async def wait(self, seconds: float):
        """等待指定时间"""
        await asyncio.sleep(seconds)
    
    async def take_screenshot(self, full_page: bool = False) -> bytes:
        """获取截图"""
        try:
            screenshot = await self.page.screenshot(full_page=full_page)
            return screenshot
        except Exception as e:
            logger.error(f"获取截图失败: {str(e)}")
            raise
    
    async def get_page_content(self) -> str:
        """获取页面内容"""
        try:
            content = await self.page.content()
            return content
        except Exception as e:
            logger.error(f"获取页面内容失败: {str(e)}")
            raise
    
    async def execute_script(self, script: str):
        """执行JavaScript代码"""
        try:
            result = await self.page.evaluate(script)
            return result
        except Exception as e:
            logger.error(f"执行脚本失败: {script}, 错误: {str(e)}")
            raise
    
    async def get_page_info(self) -> Dict[str, Any]:
        """获取页面信息"""
        try:
            return {
                "url": self.page.url,
                "title": await self.page.title(),
                "viewport": await self.page.viewport_size()
            }
        except Exception as e:
            logger.error(f"获取页面信息失败: {str(e)}")
            return {}


# 全局浏览器管理器实例
browser_manager = BrowserManager()