# websocket.py
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from config import metrics_queue, attack_queue, connected_clients

async def broadcaster():
    """Broadcast data from queues to all connected WebSocket clients and print to CLI."""
    while True:
        if not metrics_queue.empty():
            metrics = await metrics_queue.get()
            # Print metrics to CLI in a formatted way
            print(f"Metrics at {metrics['timestamp']}: "
                  f"Throughput Sent: {metrics['throughput_sent']:.2f} B/s, "
                  f"Throughput Recv: {metrics['throughput_recv']:.2f} B/s, "
                  f"Avg Latency: {metrics['aggregates']['avg_latency']:.2f} ms, "
                  f"Avg Loss: {metrics['aggregates']['avg_loss']:.2f}%")
            for client in connected_clients:
                try:
                    await client.send_json({"type": "metrics", "data": metrics})
                except Exception:
                    pass
        if not attack_queue.empty():
            attack_result = await attack_queue.get()
            # Optional: Print attack detection results to CLI
            print(f"Attack Detection Result: {attack_result}")
            for client in connected_clients:
                try:
                    await client.send_json({"type": "attack_detection", "data": attack_result})
                except Exception:
                    pass
        await asyncio.sleep(0.1)

async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections."""
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("Client disconnected")