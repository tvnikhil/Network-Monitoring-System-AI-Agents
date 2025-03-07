from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from config import metrics_queue, attack_queue, connected_clients
import logging

logger = logging.getLogger(__name__)

async def broadcaster():
    """Broadcast metrics and attack detection results to WebSocket clients."""
    while True:
        if not metrics_queue.empty():
            metrics = await metrics_queue.get()
            logger.info(f"Metrics at {metrics['timestamp']}: "
                        f"Throughput Sent: {metrics['throughput_sent']:.2f} B/s, "
                        f"Throughput Recv: {metrics['throughput_recv']:.2f} B/s, "
                        f"Avg Latency: {metrics['aggregates']['avg_latency']:.2f} ms, "
                        f"Avg Loss: {metrics['aggregates']['avg_loss']:.2f}%")
            for client in connected_clients:
                try:
                    await client.send_json({"type": "metrics", "data": metrics})
                except Exception as e:
                    logger.error(f"Error sending metrics to client: {e}")
        if not attack_queue.empty():
            attack_result = await attack_queue.get()
            logger.info(f"Attack Detection Result: {attack_result}")
            for client in connected_clients:
                try:
                    await client.send_json({"type": "attack_detection", "data": attack_result})
                except Exception as e:
                    logger.error(f"Error sending attack result to client: {e}")
        await asyncio.sleep(0.1)

async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket client connections."""
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info("Client connected")
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")