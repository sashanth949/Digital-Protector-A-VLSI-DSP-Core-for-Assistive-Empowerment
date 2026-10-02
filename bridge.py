"""
Laptop bridge: TX Pico  ->  laptop  ->  RX Pico

Reads   "TX,SINE,<noise>,<count>"      from the transmitter Pico
Sends   "RX,<MODE>,<FILTER>,<noise>"    to the receiver Pico

Setup:
    pip install pyserial
    python bridge.py --list        (shows your COM ports)
Edit TX_PORT / RX_PORT below, close Thonny, then run:
    python bridge.py
"""
import sys
import time

import serial
from serial.tools import list_ports

TX_PORT = "COM3"          # transmitter Pico
RX_PORT = "COM4"          # receiver Pico
BAUD = 115200

MODE = "AUTO"             # "AUTO" or "MANUAL"
MANUAL_FILTER = "AVG"     # used only when MODE == "MANUAL": AVG, MEDIAN or LOWPASS

SEND_INTERVAL = 0.25      # seconds between updates to the receiver


def pick_filter(noise):
    """AUTO rule (same thresholds as the earlier receiver code; tune as needed)."""
    if noise < 25:
        return "LOWPASS"
    if noise < 60:
        return "AVG"
    return "MEDIAN"


def main():
    if "--list" in sys.argv:
        for p in list_ports.comports():
            print(p.device, "-", p.description)
        return

    tx = serial.Serial(TX_PORT, BAUD, timeout=0.2)
    rx = serial.Serial(RX_PORT, BAUD, timeout=0.2)
    print("Bridge running. Ctrl+C to stop.")

    last_send = 0.0
    while True:
        raw = tx.readline().decode(errors="ignore").strip()
        if not raw.startswith("TX,"):
            continue
        parts = raw.split(",")
        try:
            noise = int(parts[2])
            count = int(parts[3])
        except (IndexError, ValueError):
            continue  # partial or garbled line

        flt = pick_filter(noise) if MODE == "AUTO" else MANUAL_FILTER

        now = time.time()
        if now - last_send >= SEND_INTERVAL:
            rx.write("RX,{},{},{}\n".format(MODE, flt, noise).encode())
            last_send = now
            print("pkt {:>6}  noise {:>3}%  ->  {} / {}".format(count, noise, MODE, flt))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
    except serial.SerialException as e:
        print("Serial error:", e)
        print("Check the COM port numbers, and make sure Thonny is closed.")