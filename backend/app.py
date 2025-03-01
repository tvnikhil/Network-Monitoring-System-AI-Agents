from fastapi import FastAPI
import asyncio
from network_monitor import PerformanceMonitoringAgent, ParameterTuningAgent, SecurityAnalysisAgent
from appWebsocket import broadcaster, websocket_endpoint  # Existing WebSocket setup
from config import metrics_queue, attack_queue  # Existing queues
from contextlib import asynccontextmanager

# Define lifespan to start agent tasks and initialize queues
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize communication queues within the event loop
    performance_to_tuning_queue = asyncio.Queue()
    tuning_to_performance_queue = asyncio.Queue()
    performance_to_security_queue = asyncio.Queue()
    security_to_performance_queue = asyncio.Queue()

    # Create agent instances with the newly created queues
    performance_agent = PerformanceMonitoringAgent(
        metrics_queue, performance_to_tuning_queue, tuning_to_performance_queue, 
        performance_to_security_queue, security_to_performance_queue
    )
    tuning_agent = ParameterTuningAgent(performance_to_tuning_queue, tuning_to_performance_queue)
    security_agent = SecurityAnalysisAgent(performance_to_security_queue, security_to_performance_queue, attack_queue)

    # Start agent tasks and broadcaster in the same event loop
    asyncio.create_task(performance_agent.run())
    asyncio.create_task(tuning_agent.run())
    asyncio.create_task(security_agent.run())
    asyncio.create_task(broadcaster())  # Existing broadcaster for WebSocket
    yield  # Application runs here

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Existing WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)