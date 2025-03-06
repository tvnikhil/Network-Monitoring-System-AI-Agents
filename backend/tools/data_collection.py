import subprocess
import asyncio

INTERFACE = "Wi-Fi"  # Use your Wi-Fi interface name 
OUTPUT_FILE = "lastCapture/capture.pcap"

def collect_data_func(duration):
    
    cmd = [
        "tshark",
        "-i", INTERFACE,
        "-a", f"duration:{duration}",
        "-w", OUTPUT_FILE
    ]