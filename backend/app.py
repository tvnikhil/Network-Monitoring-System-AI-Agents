from fastapi import FastAPI
import asyncio
from network_monitor import PerformanceMonitoringAgent, ParameterTuningAgent, SecurityAnalysisAgent
from appWebsocket import broadcaster, websocket_endpoint
from config import metrics_queue, attack_queue
from contextlib import asynccontextmanager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the application's lifecycle, initializing agents and tasks."""
    logger.info("Starting application...")
    # Initialize inter-agent communication queues
    performance_to_tuning_queue = asyncio.Queue()
    tuning_to_performance_queue = asyncio.Queue()
    performance_to_security_queue = asyncio.Queue()
    security_to_performance_queue = asyncio.Queue()

    # Instantiate agents with queues
    performance_agent = PerformanceMonitoringAgent(
        metrics_queue, performance_to_tuning_queue, tuning_to_performance_queue,
        performance_to_security_queue, security_to_performance_queue
    )
    tuning_agent = ParameterTuningAgent(performance_to_tuning_queue, tuning_to_performance_queue)
    security_agent = SecurityAnalysisAgent(performance_to_security_queue, security_to_performance_queue, attack_queue)

    # Start background tasks
    asyncio.create_task(performance_agent.run())
    asyncio.create_task(tuning_agent.run())
    asyncio.create_task(security_agent.run())
    asyncio.create_task(broadcaster())
    yield
    logger.info("Shutting down application...")

# Initialize FastAPI application
app = FastAPI(lifespan=lifespan)

# Register WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)