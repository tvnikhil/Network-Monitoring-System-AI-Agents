import subprocess
import asyncio

INTERFACE = "en0"
OUTPUT_FILE = "lastCapture/capture.pcap"

def collect_data_func(duration):
    
    cmd = [
        "tshark",
        "-i", INTERFACE,
        "-a", f"duration:{duration}",
        "-w", OUTPUT_FILE
    ]