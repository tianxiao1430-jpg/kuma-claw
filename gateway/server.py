import asyncio
import logging
from .channel_manager import ChannelManager
from .session_manager import SessionManager
from .auth_manager import AuthManager
from .agent_router import AgentRouter

logger = logging.getLogger(__name__)

class GatewayServer:
    def __init__(self, host="0.0.0.0", port=19001):
        self.host = host
        self.port = port
        self.channel_manager = ChannelManager()
        self.session_manager = SessionManager()
        self.auth_manager = AuthManager()
        self.agent_router = AgentRouter()
        
    async def start(self):
        logger.info(f"Starting Gateway Server on {self.host}:{self.port}")
        pass
        
    async def stop(self):
        logger.info("Stopping Gateway Server")
        pass
