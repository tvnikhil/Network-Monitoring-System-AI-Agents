import torch
from scapy.all import PcapReader, IP, TCP
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import matplotlib.pyplot as plt
from secretKeys import *
# import os
# os.environ["TOKENIZERS_PARALLELISM"] = "false"

class PcapClassifier:
    def __init__(self, model_name="rdpahalavan/bert-network-packet-flow-header-payload"):
        self.classes = [
            'Analysis', 'Backdoor', 'Bot', 'DDoS', 'DoS', 'DoS GoldenEye', 'DoS Hulk',
            'DoS SlowHTTPTest', 'DoS Slowloris', 'Exploits', 'FTP Patator', 'Fuzzers',
            'Generic', 'Heartbleed', 'Infiltration', 'Normal', 'Port Scan', 'Reconnaissance',
            'SSH Patator', 'Shellcode', 'Web Attack - Brute Force', 'Web Attack - SQL Injection',
            'Web Attack - XSS', 'Worms'
        ]
        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)

    def processing_packet_conversion(self, packet):
        """
        Process a packet and convert it into a feature string.
        Returns None if packet processing fails.
        """
        # Process protocol layers (if needed for extended analysis)
        packet_layer = packet
        while packet_layer:
            layer = packet_layer[0]
            if not layer.payload:
                break
            packet_layer = layer.payload

        try:
            # Extract header features
            src_port = packet.sport
            dst_port = packet.dport
            ip_length = len(packet[IP])
            ip_ttl = packet[IP].ttl
            ip_tos = packet[IP].tos
            tcp_data_offset = packet[TCP].dataofs
            tcp_flags = packet[TCP].flags

            # Process payload
            payload_bytes = bytes(packet.payload)
            payload_length = len(payload_bytes)
            payload_decimal = ' '.join(str(byte) for byte in payload_bytes)

            # Construct the feature string
            final_data = "0 0 195 -1 {} {} {} {} {} {} {} -1 {}".format(
                src_port, dst_port, ip_length, payload_length,
                ip_ttl, ip_tos, tcp_data_offset, int(tcp_flags), payload_decimal
            )
            return final_data
        except Exception:
            # If packet is malformed or missing expected layers, return None
            return None

    def classify_pcap(self, file_path, filter=None):
        """
        Process a given pcap file and return a dictionary with prediction counts.
        The 'filter' parameter is reserved for potential future use.
        """
        packets_brief = {}
        with PcapReader(file_path) as pcap:
            for pkt in pcap:
                # Process only IPv4 packets with TCP
                if IP in pkt and TCP in pkt:
                    input_line = self.processing_packet_conversion(pkt)
                    if input_line is None:
                        continue
                    # Truncate to maximum length acceptable by the model
                    truncated_line = input_line[:1024]
                    tokens = self.tokenizer(truncated_line, return_tensors="pt")
                    outputs = self.model(**tokens)
                    logits = outputs.logits
                    probabilities = logits.softmax(dim=1)
                    predicted_class = torch.argmax(probabilities, dim=1).item()
                    predicted_attack = self.classes[predicted_class]
                    packets_brief[predicted_attack] = packets_brief.get(predicted_attack, 0) + 1
        return packets_brief

    def plot_predictions(self, predictions):
        """
        Plot the prediction counts as a bar chart.
        """
        keys = list(predictions.keys())
        vals = list(predictions.values())
        plt.bar(keys, vals)
        plt.xlabel('Attack Types')
        plt.ylabel('Counts')
        plt.title('Detected Possible Attacks')
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.show()

def detect_attack_func(path):
    classifier = PcapClassifier()
    results = classifier.classify_pcap(path, filter=b"HTTP")
    print("Predictions:", str(results))
    return str(results)
    
if __name__ == '__main__':
    classifier = PcapClassifier()
    results = classifier.classify_pcap("lastCapture/capture.pcap", filter=b"HTTP")
    print("Predictions:", results)
    # classifier.plot_predictions(results)