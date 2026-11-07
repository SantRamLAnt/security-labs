#!/usr/bin/env python3
"""Summarize the Cortex-M0+ cross build: code size per object (arm-none-eabi-size), the device
state's RAM (from ram.o), and the deepest stack frame (from gcc's -fstack-usage files)."""
import glob
import subprocess

size = subprocess.run(["arm-none-eabi-size", "device.o", "sha256.o"], capture_output=True, text=True).stdout
print("  Built for the RP2040 (Arm Cortex-M0+), -Os")
print("  " + size.replace("\n", "\n  ").rstrip())
text = sum(int(l.split()[0]) for l in size.splitlines()[1:])
data = sum(int(l.split()[1]) + int(l.split()[2]) for l in size.splitlines()[1:])
nm = subprocess.run(["arm-none-eabi-nm", "-S", "ram.o"], capture_output=True, text=True).stdout.split()
ram = int(nm[1], 16)
frames = []
for f in glob.glob("*.su"):
    for line in open(f):
        loc, n, kind = line.rsplit(None, 2)
        frames.append((int(n), loc.split(":")[-1], kind))
frames.sort(reverse=True)
print(f"\n  code (text) {text:,} bytes of the Pico's 2 MB of flash ({100 * text / 2097152:.2f}%)")
print(f"  device state in RAM {ram} bytes of 264 KB ({100 * ram / 270336:.2f}%); static data {data} bytes")
print("  largest stack frames: " + ", ".join(f"{name} {n} bytes ({kind})" for n, name, kind in frames[:3]))
