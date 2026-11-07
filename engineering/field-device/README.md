# Project 3: a field device in C, with signed commands

The logic of a small remote terminal unit, written in C the way it would run on a microcontroller:
no heap, fixed-size buffers, and the same result on any byte order. It reports switch positions and
line currents and operates a tie switch on command. Every request and reply carries an HMAC-SHA256
tag and a counter. There is no board yet: it runs on the GitHub runner, and the same code is built
for the Raspberry Pi Pico's RP2040 (Arm Cortex-M0+) to measure size.

| file | what it is |
|---|---|
| `sha256.c` | SHA-256 from FIPS 180-4, HMAC from RFC 2104, a precomputed-key HMAC, constant-time compare |
| `device.c` | the device: 41-byte signed requests, 42-byte signed replies |
| `test_device.c` | test vectors, the device's rules, 1,000,000 fuzzed frames, timing |
| `sim.c` | the device behind a text line standing in for a serial port |
| `master.py` | a Python control center; sensor readings come from Lab J's node-method solver |
| `report_cross.py` | code size, RAM and stack frames from the Cortex-M0+ build |

**Request** (41 bytes): version, function, point (2), value, counter (4), then a 32-byte tag over
those 9 bytes. **Reply** (42 bytes): version, status, point (2), value (2), counter (4), tag.

The device checks, in this order: the length is exactly 41 bytes; the tag is right, compared in
constant time (a wrong tag gets no reply); the counter is higher than the last one accepted (a
replay gets a signed "replay" reply). Only then does it read the function and point. A genuine but
invalid command still uses up its counter.

## Results (run 42335465265)

- SHA-256: 5 of 5 FIPS 180-4 examples, including one million "a"s fed 1,000 bytes at a time.
- HMAC-SHA256: 6 of 6 RFC 4231 test cases (case 5 is a truncated tag and isn't used).
- C against Python's `hashlib` and `hmac`: 3,000 of 3,000 random inputs agree, every length from
  0 to 129 bytes plus longer ones.
- Any one of the 328 bits of a valid command flipped: refused every time, with no reply.
- 1,000,000 random and altered frames under AddressSanitizer and UBSan: 0 accepted, 0 replies.
- Scenario with Lab J's currents: tie open, 158.0 A at CB-101 and R-1011 and 0.0 A at SW-12; after
  a signed close, 115.0, 115.0 and 43.0 A. Forged, edited and replayed commands left the switch closed.
- Speed on the runner: SHA-256 at 235 MB/s; one tag 1,109 ns with the key hashed each time, 568 ns
  with the key state precomputed (1.95 times faster: 2 compressions instead of 4).
- Cortex-M0+ (`-Os`): 1,852 bytes of code (device 432, SHA-256 and HMAC 1,420), 248 bytes of device
  state in RAM, deepest stack frame 328 bytes (`compress`, mostly the 64-word message schedule).
  The C library's `memcpy` and `memset` aren't included.

## What it doesn't do yet

- On hardware, the counter must survive a power cut, so it would be written to flash before the
  command runs.
- The key is loaded once. A real device needs a way to install and rotate it. After the largest
  counter value the device accepts nothing until the key changes, and a test checks that.
- It hasn't run on a board. A Pico, timings on the chip and a real serial line are next.

## Running it

```
make test-asan && ./test-asan 1000000 notime   # tests and fuzzing under sanitizers
make test && ./test 1000                       # optimized build with timings
make sim && python3 master.py ./sim --check    # the control center scenario (needs numpy, pyyaml)
make cross && python3 report_cross.py          # needs gcc-arm-none-eabi
```

Built with an AI coding assistant, like the rest of this repository. Writing my own SHA-256 from
the standard, without help, and passing these same tests is how I plan to finish the C course.
