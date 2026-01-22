"""
Main entry point for LLM control plane.
"""
import uvicorn
import logging
from config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info(f"Starting LLM Control Plane on {settings.api_host}:{settings.api_port}")
    
    uvicorn.run(
        "api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )
