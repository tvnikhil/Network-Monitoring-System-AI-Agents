import json
import time
from agents.agent_monitoring import monitoring_agent
from agents.agent_parameter_tuning import parameter_tuning_agent
from common_classes import MyDeps

path_to_file = "lastCapture/capture.pcap"
initial_duration = 18
initial_cycle_interval = 2
deps = MyDeps(
    pathToFile=path_to_file,
    duration=initial_duration,
    cycle_interval=initial_cycle_interval
)
previous_attack_detected = False  # Initialize to False for the first cycle


def should_capture(last15_file, external_latency_threshold=75, external_packet_loss_threshold=5):
    try:
        with open(last15_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print("Error reading last15 file:", e)
        return False

    latencies = [dp["external_ping"].get("avg_latency") for dp in data if dp["external_ping"].get("avg_latency") is not None]
    losses = [dp["external_ping"].get("packet_loss") for dp in data if dp["external_ping"].get("packet_loss") is not None]

    if not latencies or not losses:
        print("Not enough data to determine capture conditions.")
        return False

    avg_latency = sum(latencies) / len(latencies)
    avg_loss = sum(losses) / len(losses)

    deps.avg_latency, deps.avg_loss = avg_latency, avg_loss

    print(f"Average external latency: {avg_latency:.2f} ms, Average external packet loss: {avg_loss:.2f}%")

    if avg_latency > external_latency_threshold or avg_loss > external_packet_loss_threshold:
        print("Threshold exceeded. Proceeding with capture.")
        return True
    else:
        print("Threshold not exceeded. Skipping capture.")
        return False

while True:
    print("\n=== Starting new capture cycle ===")

    if should_capture("lastCapture/last15.json"):
        # Updated prompt to include previous attack detection
        prompt = (
            f"Tune parameters based on current network conditions and previous analysis. "
            f"Current average latency: {deps.avg_latency} ms, current packet loss: {deps.avg_loss} %. "
            f"Previous attack detected: {previous_attack_detected}."
        )
        print(prompt)

        param_result = parameter_tuning_agent.run_sync(
            user_prompt=prompt,
            deps=deps
        )

        updated_params = param_result.data
        deps.duration = updated_params.duration
        deps.cycle_interval = updated_params.interval

        print(f"Updated parameters: duration = {deps.duration} sec, next cycle interval = {deps.cycle_interval} sec.")

        prompt = '''Capture the network data and Analyze the network data (location to pcap file in deps) for any signs of a network attack.
        The result from the detect_attack tool will have all possible attacks and also Normal scenario with the packet number. You have to analyse that and determine if situation is normal or the network is under attack.
        Example output is {'Normal': 39}. Here the network situation is normal as there are no attack classifications and everything is classified as normal.
        If there is a predominant attack detected, report the attack type and any other relevant information.'''

        detect_result = monitoring_agent.run_sync(
            user_prompt=prompt,
            deps=deps
        )

        print("Attack detection result:", detect_result.data)

        previous_attack_detected = detect_result.data.attack_detected
    else:
        print("No significant network anomalies. Capture cycle skipped.")

    time.sleep(deps.cycle_interval)