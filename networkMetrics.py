import psutil
import time
import subprocess
import sys
import re
from collections import deque
import json
import netifaces

def get_default_gateway():
    try:
        gateways = netifaces.gateways()
        default_gateway = gateways['default'][netifaces.AF_INET][0]
        return default_gateway
    except Exception as e:
        print("Could not determine default gateway automatically:", e)
        return None

def get_ping_metrics(host, count=4, timeout=4):
    try:
        if sys.platform.startswith("win"):
            ping_command = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
            output = subprocess.check_output(
                ping_command, stderr=subprocess.STDOUT, universal_newlines=True
            )
            loss_match = re.search(r"(\d+)% loss", output)
            packet_loss = float(loss_match.group(1)) if loss_match else None
            avg_match = re.search(r"Average = (\d+)ms", output)
            avg_latency = float(avg_match.group(1)) if avg_match else None

        else:
            # For Linux/macOS, use '-c' for count and '-W' for timeout (in seconds)
            ping_command = ["ping", "-c", str(count), "-W", str(timeout), host]
            output = subprocess.check_output(
                ping_command, stderr=subprocess.STDOUT, universal_newlines=True
            )
            loss_match = re.search(r"(\d+)% packet loss", output)
            packet_loss = float(loss_match.group(1)) if loss_match else None
            rtt_match = re.search(r"round-trip min/avg/max/stddev = [\d\.]+/([\d\.]+)/", output)
            avg_latency = float(rtt_match.group(1)) if rtt_match else None

        return {"packet_loss": packet_loss, "avg_latency": avg_latency}
    except subprocess.CalledProcessError:
        return {"packet_loss": None, "avg_latency": None}

def monitor_network_performance(interval=1, duration=60, log_file="network_log.txt", external_host="8.8.8.8", ping_count=4):
    sliding_window = deque(maxlen=15)
    io_old = psutil.net_io_counters()
    start_time = time.time()
    end_time = start_time + duration

    router_ip = get_default_gateway() or "192.168.1.1"
    print(f"Using local gateway (router) IP: {router_ip}")

    total_bytes_sent = 0
    total_bytes_recv = 0

    with open(log_file, "a") as file:
        file.write(f"\n--- Monitoring started at {time.ctime(start_time)} ---\n")
        while time.time() < end_time:
            time.sleep(interval)
            current_time = time.time()

            io_new = psutil.net_io_counters()
            bytes_sent = io_new.bytes_sent - io_old.bytes_sent
            bytes_recv = io_new.bytes_recv - io_old.bytes_recv
            total_bytes_sent += bytes_sent
            total_bytes_recv += bytes_recv

            throughput_sent = bytes_sent / interval
            throughput_recv = bytes_recv / interval

            external_ping = get_ping_metrics(host=external_host, count=ping_count)

            local_ping = get_ping_metrics(host=router_ip, count=ping_count)

            data_point = {
                "timestamp": time.ctime(current_time),
                "bytes_sent": bytes_sent,
                "bytes_recv": bytes_recv,
                "throughput_sent": throughput_sent,
                "throughput_recv": throughput_recv,
                "external_ping": external_ping,
                "local_ping": local_ping
            }
            
            sliding_window.append(data_point)
            
            with open("last15.json", "w") as outfile:
                json.dump(list(sliding_window), outfile, indent=2)
            
            log_line = (
                f"Time: {data_point['timestamp']} | "
                f"Bytes Sent: {bytes_sent} | Bytes Received: {bytes_recv} | "
                f"Throughput Sent: {throughput_sent:.2f} B/s | "
                f"Throughput Received: {throughput_recv:.2f} B/s | \n"
                f"External ({external_host}) -> Packet Loss: "
                f"{external_ping.get('packet_loss', 'N/A')}% | Avg Latency: "
                f"{external_ping.get('avg_latency', 'N/A')} ms | \n"
                f"Local Gateway ({router_ip}) -> Packet Loss: "
                f"{local_ping.get('packet_loss', 'N/A')}% | Avg Latency: "
                f"{local_ping.get('avg_latency', 'N/A')} ms\n"
            )
            print(log_line, end="", flush=True)
            file.write(log_line)
            
            io_old = io_new

        total_time = time.time() - start_time
        average_throughput_sent = total_bytes_sent / total_time
        average_throughput_recv = total_bytes_recv / total_time

        summary = (
            "\n--- Summary ---\n"
            f"Monitoring Duration: {total_time:.2f} seconds\n"
            f"Total Bytes Sent: {total_bytes_sent}\n"
            f"Total Bytes Received: {total_bytes_recv}\n"
            f"Average Throughput Sent: {average_throughput_sent:.2f} B/s\n"
            f"Average Throughput Received: {average_throughput_recv:.2f} B/s\n"
            f"Monitoring ended at {time.ctime()}\n"
            "-------------------------\n"
        )
        print(summary, flush=True)
        file.write(summary)

if __name__ == "__main__":
    
    monitor_network_performance(
        interval=0.75,
        duration=150,
        log_file="network_log.txt",
        external_host="8.8.8.8",   # External connectivity test
        ping_count=4
    )