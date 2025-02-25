# import subprocess
# import os
from PcapAnalysis import *

def detect_attack_func(path):
    classifier = PcapClassifier()
    results = classifier.classify_pcap(path, filter=b"HTTP")
    print("Predictions:", str(results))
    return str(results)
    # working_dir = os.path.join(os.path.dirname(__file__), "lucid-ddos")
    # cmd1 = [
    # 'python', 'lucid_dataset_parser.py',
    # '--dataset_folder', path,
    # '--dataset_type', 'DOS2019',
    # '--packets_per_flow', '10',
    # '--dataset_id', 'MYPCAP',
    # '--traffic_type', 'all',
    # '--time_window', '10'
    # ]

    # # Command 2: Preprocess the dataset
    # cmd2 = [
    #     'python', 'lucid_dataset_parser.py',
    #     '--preprocess_folder', path
    # ]

    # # Command 3: Run the CNN model for prediction
    # cmd3 = [
    #     'python', 'lucid_cnn.py',
    #     '--predict', path,
    #     '--model', './output/10t-10n-DOS2019-LUCID.h5'
    # ]

    # # Function to execute a command and handle errors
    # def execute_command(command):
    #     last_command_output = None
    #     try:
    #         result = subprocess.run(command, check=True, text=True, capture_output=True, cwd=working_dir)
    #         last_command_output = result.stdout
    #         print(f"Command {' '.join(command)} executed successfully.")
    #         print("Output:")
    #         print(result.stdout)
    #     except subprocess.CalledProcessError as e:
    #         print(f"Error occurred while executing {' '.join(command)}:")
    #         print(e.stderr)
        
    #     return last_command_output

    # # Execute the commands sequentially
    # for cmd in [cmd1, cmd2, cmd3]:
    #     op = execute_command(cmd)
    
    # # print(op)
    # return op

# detect_attack_func("my-pcap-files")