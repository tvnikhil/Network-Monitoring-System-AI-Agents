from fastapi import FastAPI
import asyncio
from network_monitor import NetworkMonitor
from backend.appWebsocket import broadcaster, websocket_endpoint

monitor = NetworkMonitor()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(monitor.collect_metrics(interval=2))
    asyncio.create_task(monitor.attack_detection_loop())
    asyncio.create_task(broadcaster())
    yield

app = FastAPI(lifespan=lifespan)

app.websocket("/ws")(websocket_endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)