import os
from collections import deque
import asyncio
from common_classes import MyDeps
from tools.data_collection import INTERFACE

# Environment setup
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Global variables
connected_clients = set()
metrics_queue = asyncio.Queue()
attack_queue = asyncio.Queue()

# NetworkMonitor configuration
DEFAULT_DEPS = MyDeps(
    pathToFile="lastCapture/capture.pcap",
    duration=18,
    cycle_interval=1
)
SLIDING_WINDOW_MAXLEN = 15