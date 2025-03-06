from collections import deque
import asyncio
import subprocess
import psutil
import time
from agents.agent_monitoring import monitoring_agent  # For attack analysis
from agents.agent_parameter_tuning import parameter_tuning_agent  # For parameter tuning
from common_classes import MyDeps, AnalysisResult  # Assuming these exist
from config import metrics_queue, attack_queue  # Existing queues for broadcasting
from utils import get_ping_metrics, get_default_gateway  # Utility functions

# Network interface for capture (adjust as needed)

INTERFACE = "Wi-Fi"  # Use your Wi-Fi interface name 
# Performance Monitoring Agent
class PerformanceMonitoringAgent:
    def __init__(self, metrics_queue, performance_to_tuning_queue, tuning_to_performance_queue, 
                 performance_to_security_queue, security_to_performance_queue):
        self.metrics_queue = metrics_queue
        self.performance_to_tuning_queue = performance_to_tuning_queue
        self.tuning_to_performance_queue = tuning_to_performance_queue
        self.performance_to_security_queue = performance_to_security_queue
        self.security_to_performance_queue = security_to_performance_queue
        self.sliding_window = deque(maxlen=15)  # Sliding window for metrics
        self.deps = MyDeps(pathToFile="lastCapture/capture.pcap", duration=18, cycle_interval=1)
        self.previous_attack_detected = False  # Track prior attack status
        self.last_check_time = time.time()  # For timing anomaly checks

    async def collect_metrics(self):
        """Collect network metrics and update sliding window."""
        io_old = psutil.net_io_counters()
        router_ip = get_default_gateway() or "192.168.1.1"
        await asyncio.sleep(0.1)  # Brief delay to measure I/O difference
        io_new = psutil.net_io_counters()
        bytes_sent = io_new.bytes_sent - io_old.bytes_sent
        bytes_recv = io_new.bytes_recv - io_old.bytes_recv
        throughput_sent = bytes_sent / 2  # Assuming 2-second interval
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
        
        # Calculate aggregates
        if self.sliding_window:
            latencies = [dp["external_ping"]["avg_latency"] for dp in self.sliding_window 
                        if dp["external_ping"]["avg_latency"] is not None]
            losses = [dp["external_ping"]["packet_loss"] for dp in self.sliding_window 
                      if dp["external_ping"]["packet_loss"] is not None]
            if latencies and losses:
                aggregates = {
                    "avg_latency": sum(latencies) / len(latencies),
                    "avg_loss": sum(losses) / len(losses),
                    "max_latency": max(latencies),
                    "max_loss": max(losses)
                }
            else:
                aggregates = None
            data_point["aggregates"] = aggregates
        await self.metrics_queue.put(data_point)  # Broadcast metrics

    def _should_capture(self):
        """Check if an anomaly warrants PCAP capture."""
        if not self.sliding_window:
            return False
        latencies = [dp["external_ping"]["avg_latency"] for dp in self.sliding_window 
                    if dp["external_ping"]["avg_latency"] is not None]
        losses = [dp["external_ping"]["packet_loss"] for dp in self.sliding_window 
                  if dp["external_ping"]["packet_loss"] is not None]
        if not latencies or not losses:
            return False
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        avg_loss = sum(losses) / len(losses)
        max_loss = max(losses)
        return (avg_latency > 75) or (max_latency > 100) or (avg_loss > 5) or (max_loss > 10)

    async def capture_pcap(self):
        """Capture network traffic using tshark."""
        print(f"Capturing data for {self.deps.duration} seconds...")
        capture_result = await asyncio.to_thread(
            subprocess.run,
            ["tshark", "-i", INTERFACE, "-a", f"duration:{self.deps.duration}", "-w", self.deps.pathToFile],
            capture_output=True,
            text=True
        )
        if capture_result.returncode != 0:
            print(f"Capture failed: {capture_result.stderr}")

    async def metric_collection_loop(self):
        """Collect metrics every 2 seconds."""
        while True:
            await self.collect_metrics()
            await asyncio.sleep(2)

    async def anomaly_checking_loop(self):
        """Check for anomalies based on cycle_interval."""
        while True:
            current_time = time.time()
            if current_time - self.last_check_time >= self.deps.cycle_interval:
                self.last_check_time = current_time
                if self._should_capture():
                    print("Anomaly detected, coordinating with team.")
                    # Send metrics and attack status to ParameterTuningAgent
                    await self.performance_to_tuning_queue.put({
                        "metrics": self.sliding_window[-1],
                        "previous_attack_detected": self.previous_attack_detected
                    })
                    # Receive updated parameters
                    updated_deps = await self.tuning_to_performance_queue.get()
                    self.deps.duration = updated_deps.duration
                    self.deps.cycle_interval = updated_deps.cycle_interval
                    # Capture PCAP
                    await self.capture_pcap()
                    # Send PCAP path to SecurityAnalysisAgent
                    await self.performance_to_security_queue.put(self.deps.pathToFile)
                    # Receive analysis result
                    analysis_result = await self.security_to_performance_queue.get()
                    self.previous_attack_detected = analysis_result.attack_detected
                    self.sliding_window.clear()
            await asyncio.sleep(1)  # Check every second

    async def run(self):
        """Run both loops concurrently."""
        await asyncio.gather(
            self.metric_collection_loop(),
            self.anomaly_checking_loop()
        )

# Parameter Tuning Agent
class ParameterTuningAgent:
    def __init__(self, performance_to_tuning_queue, tuning_to_performance_queue):
        self.performance_to_tuning_queue = performance_to_tuning_queue
        self.tuning_to_performance_queue = tuning_to_performance_queue

    async def run(self):
        """Tune parameters based on network conditions."""
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

# Security Analysis Agent
class SecurityAnalysisAgent:
    def __init__(self, performance_to_security_queue, security_to_performance_queue, attack_queue):
        self.performance_to_security_queue = performance_to_security_queue
        self.security_to_performance_queue = security_to_performance_queue
        self.attack_queue = attack_queue

    async def analyze_pcap(self, pcap_path):
        """Analyze PCAP for attacks."""
        print("Analyzing PCAP for attacks...")
        detect_result = await monitoring_agent.run(
            user_prompt="Analyze the network data for attacks.",
            deps=MyDeps(pathToFile=pcap_path)
        )
        # Broadcast result
        await self.attack_queue.put({
            "attack_detected": detect_result.data.attack_detected,
            "details": detect_result.data.details
        })
        # Send result back to PerformanceMonitoringAgent
        await self.security_to_performance_queue.put(detect_result.data)

    async def run(self):
        """Process PCAPs as they arrive."""
        while True:
            pcap_path = await self.performance_to_security_queue.get()
            await self.analyze_pcap(pcap_path)