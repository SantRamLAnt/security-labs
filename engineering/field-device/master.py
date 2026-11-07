#!/usr/bin/env python3
"""The control center side: talks to the C device over a text "serial line" (sim.c).

1. Cross-checks the C SHA-256 and HMAC against Python's hashlib and hmac on 3,000 random inputs,
   including every length around the padding boundaries (55, 56, 63, 64 bytes and so on).
2. Runs a scenario against the device. The sensor readings are not made up: Lab J's node-method
   solver (labs/lab-j/grid/nodal.py) computes the phase A currents for the synthetic feeder with
   tie switch SW-12 open, and again with it closed, and those are what the simulated sensors read.
   The control center closes SW-12 with a signed command, the "physics" moves the currents to
   the closed-tie solution, and the readings the device signs and sends back are compared with
   the model. Then an attacker without the key tries to forge, alter and replay commands.

Python's own hmac module builds and checks every frame here, so the C code is being tested by a
separate implementation, not by itself.

Usage: master.py PATH_TO_SIM [--check]
"""
import hashlib
import hmac
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "labs" / "lab-j" / "grid"))
import nodal  # noqa: E402

READ_ANALOG, READ_SWITCH, OPERATE = 0x01, 0x02, 0x05
STATUS = {0: "OK", 3: "bad version", 4: "replay", 5: "bad function", 6: "bad point", 7: "bad value"}
POINTS = ["CB-101", "R-1011", "SW-12"]


class Device:
    def __init__(self, path):
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)

    def cmd(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        return self.p.stdout.readline().strip()

    def close(self):
        self.cmd("QUIT")
        self.p.wait(timeout=5)


def request(key, function, point, value, counter):
    body = struct.pack(">BBHBI", 1, function, point, value, counter)
    return body + hmac.new(key, body, hashlib.sha256).digest()


def parse_reply(key, line):
    """Returns (status, point, value, counter, tag_ok) for a REPLY, or ('silent', code) for SILENT."""
    kind, data = line.split(" ", 1)
    if kind == "SILENT":
        return ("silent", int(data))
    raw = bytes.fromhex(data)
    body, tag = raw[:10], raw[10:]
    _, status, point, value, counter = struct.unpack(">BBHHI", body)
    ok = hmac.compare_digest(tag, hmac.new(key, body, hashlib.sha256).digest())
    return (STATUS.get(status, status), point, value, counter, ok)


def cross_check(dev):
    rng = random.Random(20261106)
    lengths = list(range(0, 130)) + [rng.randint(130, 1500) for _ in range(370)]
    bad = 0
    for i in range(3000):
        n = lengths[i % len(lengths)]
        msg = bytes(rng.getrandbits(8) for _ in range(n))
        if i % 2 == 0:
            got = dev.cmd(f"HASH {msg.hex() or '-'}").split()[1]
            bad += got != hashlib.sha256(msg).hexdigest()
        else:
            key = bytes(rng.getrandbits(8) for _ in range(rng.choice([0, 1, 20, 32, 63, 64, 65, 131])))
            got = dev.cmd(f"HMAC {key.hex() or '-'} {msg.hex() or '-'}").split()[1]
            bad += got != hmac.new(key, msg, hashlib.sha256).hexdigest()
    return bad


def model_currents():
    """Phase A currents (tenths of an amp) from Lab J's node method, tie open and tie closed."""
    path = ROOT / "labs" / "lab-j" / "grid" / "feeder-normal.yaml"
    m = yaml.safe_load(path.read_text())
    out = {}
    out["open"] = nodal.analyse(str(path))["phases"][0]["sections"]
    for f in m["feeders"]:
        for d in f["devices"]:
            if d["id"] == "SW-12":
                d["normal"] = "closed"
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as t:
        yaml.safe_dump(m, t)
    out["closed"] = nodal.analyse(t.name)["phases"][0]["sections"]
    os.unlink(t.name)
    return {k: [round(10 * abs(v.get(p, 0.0))) for p in POINTS] for k, v in out.items()}


def main():
    sim = sys.argv[1]
    dev = Device(sim)
    results = []

    def check(name, ok):
        results.append((name, bool(ok)))

    bad = cross_check(dev)
    print(f"  Cross-check against Python hashlib and hmac: {3000 - bad} of 3000 agree")
    check("C SHA-256 and HMAC match Python on 3,000 random inputs", bad == 0)

    model = model_currents()
    key = os.urandom(32)                      # a fresh shared key every run; never written down
    attacker_key = os.urandom(32)
    dev.cmd(f"KEY {key.hex()}")
    for i, v in enumerate(model["open"]):
        dev.cmd(f"SET {i} {v}")
    counter = 0

    def send(frame):
        return parse_reply(key, dev.cmd(f"FRAME {frame.hex()}"))

    def next_req(function, point, value=0):
        nonlocal counter
        counter += 1
        return request(key, function, point, value, counter)

    print("\n  Lab J's node method, phase A currents the simulated sensors will read (amps)")
    print("                 " + "  ".join(f"{p:>7s}" for p in POINTS))
    for k in ("open", "closed"):
        print(f"    SW-12 {k:<7s}" + "  ".join(f"{v / 10:7.1f}" for v in model[k]))

    print("\n  Scenario                                   device answer        tag   switch")
    log = []

    def step(name, reply, ok_expected=None):
        state = dev.cmd("STATE").split()
        sw = "closed" if state[1] == "1" else "open"
        if reply[0] == "silent":
            ans, tag = "no reply", "-"
        else:
            ans = f"{reply[0]}" + (f", {reply[2] / 10:.1f} A" if reply[0] == "OK" and name.startswith("read") else "")
            tag = "valid" if reply[4] else "BAD"
        print(f"    {name:<41s}  {ans:<19s}  {tag:<5s} {sw}")
        log.append((name, reply, sw))
        return reply, sw

    readings_open = []
    for i, p in enumerate(POINTS):
        r, _ = step(f"read {p} current", send(next_req(READ_ANALOG, i)))
        readings_open.append(r[2])
    close_frame = next_req(OPERATE, 0, 1)
    r, sw = step("close SW-12 (signed)", send(close_frame))
    check("signed close accepted and switch closed", r[0] == "OK" and r[4] and sw == "closed")
    for i, v in enumerate(model["closed"]):     # the physics: the feeder now runs looped
        dev.cmd(f"SET {i} {v}")
    readings_closed = []
    for i, p in enumerate(POINTS):
        r, _ = step(f"read {p} current", send(next_req(READ_ANALOG, i)))
        readings_closed.append(r[2])
    check("readings match Lab J's model, tie open", readings_open == model["open"])
    check("readings match Lab J's model, tie closed", readings_closed == model["closed"])
    check("every signed reply's tag checks out in Python", all(x[1][4] for x in log if x[1][0] != "silent"))

    print("    -- an attacker on the line, without the key --")
    forged = request(attacker_key, OPERATE, 0, 0, counter + 1)
    r, sw = step("forged open command (wrong key)", send(forged))
    check("forged command: no reply, switch still closed", r[0] == "silent" and sw == "closed")
    tampered = bytearray(close_frame)
    tampered[4] = 0                             # change "close" to "open", keep the old tag
    tampered[8] = (counter + 2) & 0xFF          # and bump the counter
    r, sw = step("captured close, edited to open", send(bytes(tampered)))
    check("edited command: no reply, switch still closed", r[0] == "silent" and sw == "closed")
    r, sw = step("captured close, replayed as is", send(close_frame))
    check("replayed command: refused as a replay with a signed reply", r[0] == "replay" and r[4])
    r, sw = step("open SW-12 (signed, control center)", send(next_req(OPERATE, 0, 0)))
    check("the real control center can still open it", r[0] == "OK" and sw == "open")

    state = dev.cmd("STATE").split()
    print(f"\n  Device counters: {state[5]} accepted, {state[6]} refused")
    dev.close()

    print()
    for name, ok in results:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
    failed = sum(not ok for _, ok in results)
    if "--check" in sys.argv:
        print("\n  check:", "PASS" if not failed else f"FAIL ({failed})")
        sys.exit(failed)


if __name__ == "__main__":
    main()
