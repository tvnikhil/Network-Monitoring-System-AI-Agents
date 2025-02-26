import subprocess
import os

# Define your network interface and capture settings
INTERFACE = "en0"  # Replace with your actual interface name
# OUTPUT_DIR = os.path.join("lucid-ddos", "my-pcap-files")
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

# # Example usage
# if __name__ == "__main__":
#     collect_data_func(5)
