from collections import deque
import asyncio
import subprocess
import psutil
import time
from agents.agent_monitoring import monitoring_agent
from agents.agent_parameter_tuning import parameter_tuning_agent
from common_classes import MyDeps, AnalysisResult
from config import metrics_queue, attack_queue, SLIDING_WINDOW_MAXLEN
from utils import get_ping_metrics, get_default_gateway
import logging

logger = logging.getLogger(__name__)

INTERFACE = "Wi-Fi"  # Network interface for capture

class PerformanceMonitoringAgent:
    def __init__(self, metrics_queue: asyncio.Queue, performance_to_tuning_queue: asyncio.Queue,
                 tuning_to_performance_queue: asyncio.Queue, performance_to_security_queue: asyncio.Queue,
                 security_to_performance_queue: asyncio.Queue):
        self.metrics_queue = metrics_queue
        self.performance_to_tuning_queue = performance_to_tuning_queue
        self.tuning_to_performance_queue = tuning_to_performance_queue
        self.performance_to_security_queue = performance_to_security_queue
        self.security_to_performance_queue = security_to_performance_queue
        self.sliding_window = deque(maxlen=SLIDING_WINDOW_MAXLEN)
        self.deps = MyDeps(pathToFile="lastCapture/capture.pcap", duration=18, cycle_interval=1)
        self.previous_attack_detected = False
        self.last_check_time = time.time()

    async def collect_metrics(self) -> None:
        """Collect network metrics and update the sliding window."""
        io_old = psutil.net_io_counters()
        router_ip = get_default_gateway() or "192.168.1.1"
        await asyncio.sleep(0.1)
        io_new = psutil.net_io_counters()
        bytes_sent = io_new.bytes_sent - io_old.bytes_sent
        bytes_recv = io_new.bytes_recv - io_old.bytes_recv
        throughput_sent = bytes_sent / 2
        throughput_recv = bytes_recv / 2
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

        if self.sliding_window:
            latencies = [dp["external_ping"]["avg_latency"] for dp in self.sliding_window if dp["external_ping"]["avg_latency"] is not None]
            losses = [dp["external_ping"]["packet_loss"] for dp in self.sliding_window if dp["external_ping"]["packet_loss"] is not None]
            aggregates = {
                "avg_latency": sum(latencies) / len(latencies) if latencies else None,
                "avg_loss": sum(losses) / len(losses) if losses else None,
                "max_latency": max(latencies) if latencies else None,
                "max_loss": max(losses) if losses else None
            }
            data_point["aggregates"] = aggregates
        await self.metrics_queue.put(data_point)

    def _should_capture(self) -> bool:
        """Determine if an anomaly requires PCAP capture."""
        if not self.sliding_window:
            return False
        latencies = [dp["external_ping"]["avg_latency"] for dp in self.sliding_window if dp["external_ping"]["avg_latency"] is not None]
        losses = [dp["external_ping"]["packet_loss"] for dp in self.sliding_window if dp["external_ping"]["packet_loss"] is not None]
        if not latencies or not losses:
            return False
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        avg_loss = sum(losses) / len(losses)
        max_loss = max(losses)
        return (avg_latency > 75) or (max_latency > 100) or (avg_loss > 5) or (max_loss > 10)

    async def capture_pcap(self) -> None:
        """Capture network traffic using tshark."""
        logger.info(f"Capturing data for {self.deps.duration} seconds...")
        try:
            capture_result = await asyncio.to_thread(
                subprocess.run,
                ["tshark", "-i", INTERFACE, "-a", f"duration:{self.deps.duration}", "-w", self.deps.pathToFile],
                capture_output=True,
                text=True
            )
            if capture_result.returncode != 0:
                logger.error(f"Capture failed: {capture_result.stderr}")
        except Exception as e:
            logger.error(f"Error during capture: {e}")

    async def metric_collection_loop(self) -> None:
        """Periodically collect network metrics."""
        while True:
            await self.collect_metrics()
            await asyncio.sleep(2)

    async def anomaly_checking_loop(self) -> None:
        """Monitor for anomalies based on cycle interval."""
        while True:
            current_time = time.time()
            if current_time - self.last_check_time >= self.deps.cycle_interval:
                self.last_check_time = current_time
                if self._should_capture():
                    logger.info("Anomaly detected, coordinating with team.")
                    await self.performance_to_tuning_queue.put({
                        "metrics": self.sliding_window[-1],
                        "previous_attack_detected": self.previous_attack_detected
                    })
                    updated_deps = await self.tuning_to_performance_queue.get()
                    self.deps.duration = updated_deps.duration
                    self.deps.cycle_interval = updated_deps.cycle_interval
                    await self.capture_pcap()
                    await self.performance_to_security_queue.put(self.deps.pathToFile)
                    analysis_result = await self.security_to_performance_queue.get()
                    self.previous_attack_detected = analysis_result.attack_detected
                    self.sliding_window.clear()
            await asyncio.sleep(1)

    async def run(self) -> None:
        """Execute metric collection and anomaly checking concurrently."""
        await asyncio.gather(
            self.metric_collection_loop(),
            self.anomaly_checking_loop()
        )

class ParameterTuningAgent:
    def __init__(self, performance_to_tuning_queue: asyncio.Queue, tuning_to_performance_queue: asyncio.Queue):
        self.performance_to_tuning_queue = performance_to_tuning_queue
        self.tuning_to_performance_queue = tuning_to_performance_queue

    async def run(self) -> None:
        """Adjust monitoring parameters based on network conditions."""
        while True:
            data = await self.performance_to_tuning_queue.get()
            metrics = data["metrics"]
            previous_attack_detected = data["previous_attack_detected"]
            prompt = (
                f"Tune parameters based on current network conditions and previous analysis. "
                f"Current average latency: {metrics['aggregates']['avg_latency']} ms, "
                f"current packet loss: {metrics['aggregates']['avg_loss']} %. "
                f"Previous attack detected: {previous_attack_detected}."
            )
            param_result = await parameter_tuning_agent.run(user_prompt=prompt, deps=MyDeps())
            updated_deps = MyDeps(duration=param_result.data.duration, cycle_interval=param_result.data.interval)
            await self.tuning_to_performance_queue.put(updated_deps)

class SecurityAnalysisAgent:
    def __init__(self, performance_to_security_queue: asyncio.Queue, security_to_performance_queue: asyncio.Queue, attack_queue: asyncio.Queue):
        self.performance_to_security_queue = performance_to_security_queue
        self.security_to_performance_queue = security_to_performance_queue
        self.attack_queue = attack_queue

    async def analyze_pcap(self, pcap_path: str) -> None:
        """Analyze PCAP files for potential attacks."""
        logger.info("Analyzing PCAP for attacks...")
        try:
            detect_result = await monitoring_agent.run(
                user_prompt="Analyze the network data for attacks.",
                deps=MyDeps(pathToFile=pcap_path)
            )
            await self.attack_queue.put({
                "attack_detected": detect_result.data.attack_detected,
                "details": detect_result.data.details
            })
            await self.security_to_performance_queue.put(detect_result.data)
        except Exception as e:
            logger.error(f"Error during analysis: {e}")

    async def run(self) -> None:
        """Process incoming PCAP files for analysis."""
        while True:
            pcap_path = await self.performance_to_security_queue.get()
            await self.analyze_pcap(pcap_path)