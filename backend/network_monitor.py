# network_monitor.py
from collections import deque
import asyncio
import subprocess
import psutil
import time
from agents.agent_monitoring import monitoring_agent
from agents.agent_parameter_tuning import parameter_tuning_agent
from common_classes import AnalysisResult
from config import metrics_queue, attack_queue, DEFAULT_DEPS, SLIDING_WINDOW_MAXLEN
from utils import get_ping_metrics, get_default_gateway

INTERFACE = "en0"

class NetworkMonitor:
    def __init__(self):
        self.sliding_window = deque(maxlen=SLIDING_WINDOW_MAXLEN)
        self.deps = DEFAULT_DEPS
        self.previous_attack_detected = False

    async def collect_metrics(self, interval: float = 1):
        """Collect network metrics, calculate aggregates, and send to metrics_queue."""
        io_old = psutil.net_io_counters()
        router_ip = get_default_gateway() or "192.168.1.1"
        
        while True:
            await asyncio.sleep(interval)
            io_new = psutil.net_io_counters()
            bytes_sent = io_new.bytes_sent - io_old.bytes_sent
            bytes_recv = io_new.bytes_recv - io_old.bytes_recv
            throughput_sent = bytes_sent / interval
            throughput_recv = bytes_recv / interval
            external_ping = await get_ping_metrics("8.8.8.8")
            local_ping = await get_ping_metrics(router_ip)
            
            data_point = {
                "timestamp": time.ctime(),
                "bytes_sent": bytes_sent,
                "bytes_recv": bytes_recv,
                "throughput_sent": throughput_sent,
                "throughput_recv": throughput_recv,
                "external_ping": external_ping,
                "local_ping": local_ping
            }
            self.sliding_window.append(data_point)
            
            # Calculate aggregated metrics
            if self.sliding_window:
                latencies = [dp["external_ping"]["avg_latency"] for dp in self.sliding_window if dp["external_ping"]["avg_latency"] is not None]
                losses = [dp["external_ping"]["packet_loss"] for dp in self.sliding_window if dp["external_ping"]["packet_loss"] is not None]
                if latencies and losses:
                    max_latency = max(latencies)
                    max_loss = max(losses)
                    avg_latency = sum(latencies) / len(latencies)
                    avg_loss = sum(losses) / len(losses)
                    aggregates = {
                        "avg_latency": avg_latency,
                        "avg_loss": avg_loss,
                        "max_latency": max_latency,
                        "max_loss": max_loss
                    }
                else:
                    aggregates = None
            else:
                aggregates = None
            
            data_point["aggregates"] = aggregates
            
            await metrics_queue.put(data_point)
            io_old = io_new
            await asyncio.sleep(0.1)

    async def attack_detection_loop(self):
        """Run the attack detection loop and send results to attack_queue."""
        while True:
            try:
                if self._should_capture():
                    print("Capture triggered.")  # Keep this for significant events
                    prompt = (
                        f"Tune parameters based on current network conditions and previous analysis. "
                        f"Current average latency: {self.deps.avg_latency} ms, current packet loss: {self.deps.avg_loss} %. "
                        f"Previous attack detected: {self.previous_attack_detected}."
                    )
                    print("Tuning parameters...")
                    param_result = await parameter_tuning_agent.run(user_prompt=prompt, deps=self.deps)
                    self.deps.duration = param_result.data.duration
                    self.deps.cycle_interval = param_result.data.interval
                    print(f"Updated parameters: duration = {self.deps.duration} sec, next cycle interval = {self.deps.cycle_interval} sec.")

                    print(f"Capturing data for {self.deps.duration} seconds...")
                    capture_result = await asyncio.to_thread(
                        subprocess.run,
                        ["tshark", "-i", INTERFACE, "-a", f"duration:{self.deps.duration}", "-w", self.deps.pathToFile],
                        capture_output=True,
                        text=True
                    )
                    if capture_result.returncode != 0:
                        print(f"Capture failed: {capture_result.stderr}")
                        continue

                    print("Analyzing for attacks...")
                    detect_result = await monitoring_agent.run(
                        user_prompt="Analyze the network data once for attacks.",
                        deps=self.deps
                    )
                    self.previous_attack_detected = detect_result.data.attack_detected
                    await attack_queue.put({
                        "attack_detected": detect_result.data.attack_detected,
                        "details": detect_result.data.details
                    })
                # Removed "No capture needed" print to reduce frequency
            except Exception as e:
                print(f"Error in attack detection loop: {e}")
            await asyncio.sleep(self.deps.cycle_interval)

    def _should_capture(self, latency_threshold=75, loss_threshold=5) -> bool:
        if not self.sliding_window:
            return False
        latencies = [dp["external_ping"]["avg_latency"] for dp in self.sliding_window if dp["external_ping"]["avg_latency"] is not None]
        losses = [dp["external_ping"]["packet_loss"] for dp in self.sliding_window if dp["external_ping"]["packet_loss"] is not None]
        if not latencies or not losses:
            # print("No valid latency or loss data")  # Commented out
            return False
        max_latency = max(latencies)
        max_loss = max(losses)
        avg_latency = sum(latencies) / len(latencies)
        avg_loss = sum(losses) / len(losses)
        # Comment out frequent prints
        # print(f"Average latency: {avg_latency:.2f} ms, Average packet loss: {avg_loss:.2f}%")
        decision = (avg_latency > 75) or (max_latency > 100) or (avg_loss > 5) or (max_loss > 10)
        # print(f"Capture decision: {decision}")
        return decision