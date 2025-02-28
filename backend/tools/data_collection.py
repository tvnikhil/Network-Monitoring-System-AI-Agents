import subprocess

INTERFACE = "en0"
OUTPUT_FILE = "lastCapture/capture.pcap"

def collect_data_func(duration):
    
    cmd = [
        "tshark",
        "-i", INTERFACE,
        "-a", f"duration:{duration}",
        "-w", OUTPUT_FILE
    ]
    print(f"Starting capture on {INTERFACE} for {duration} seconds...")
    subprocess.run(cmd)
    print(f"Capture complete. PCAP file saved as '{OUTPUT_FILE}'.")