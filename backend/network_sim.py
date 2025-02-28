import subprocess
import sys
import os

def enable_dummynet(delay='150ms', loss=0.1):
    try:
        print("Enabling packet filter (pfctl)...")
        subprocess.run(["sudo", "pfctl", "-E"], check=True)
        
        print(f"Configuring dummynet pipe with delay {delay} and packet loss rate {loss}...")
        subprocess.run(["sudo", "dnctl", "pipe", "1", "config", "delay", delay, "plr", str(loss)], check=True)
        
        # Create a temporary pf configuration file.
        pf_conf = "dummynet in quick all pipe 1\ndummynet out quick all pipe 1\n"
        temp_pf_file = "/tmp/pf.conf"
        with open(temp_pf_file, "w") as f:
            f.write(pf_conf)
        print("Loading pf configuration...")
        subprocess.run(["sudo", "pfctl", "-f", temp_pf_file], check=True)
        
        print("Dummynet enabled: traffic will now experience delay and packet loss.")
    except subprocess.CalledProcessError as e:
        print("An error occurred while enabling dummynet:", e)
        sys.exit(1)

def disable_dummynet():
    try:
        print("Restoring original pf configuration...")
        subprocess.run(["sudo", "pfctl", "-F", "all", "-f", "/etc/pf.conf"], check=True)
        print("Flushing dummynet pipes...")
        subprocess.run(["sudo", "dnctl", "-q", "flush"], check=True)
        print("Dummynet disabled: normal network conditions restored.")
    except subprocess.CalledProcessError as e:
        print("An error occurred while disabling dummynet:", e)
        sys.exit(1)

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("Please run this script with sudo or as root.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: sudo python3 network_sim.py [enable|disable] [optional:delay] [optional:loss]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    if command == "enable":
        delay = sys.argv[2] if len(sys.argv) > 2 else "100ms"
        loss = sys.argv[3] if len(sys.argv) > 3 else 0.1
        try:
            loss = float(loss)
        except ValueError:
            print("Loss value must be a float (e.g., 0.1 for 10%).")
            sys.exit(1)
        enable_dummynet(delay=delay, loss=loss)
    elif command == "disable":
        disable_dummynet()
    else:
        print("Unknown command. Use 'enable' or 'disable'.")