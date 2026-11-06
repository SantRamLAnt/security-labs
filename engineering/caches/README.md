# Measuring the memory hierarchy

`memory_hierarchy.py` measures the caches described in MIT 6.004, Chapter 14 (Caches and the
Memory Hierarchy), from Python with NumPy:

1. **Random reads** from arrays of 16 KiB to 512 MiB. The time per read climbs in steps as the
   array outgrows each cache level reported by `lscpu`.
2. **Strided reads** of a 256 MiB array. Up to a stride of 8 values (one 64-byte cache line),
   each step wastes more of every line fetched.

Two things I'd flag. The simple cache-line model says the time per value should level off past
a stride of 8, and on the machines I've tried it keeps rising. Prefetching and memory pages are
the likely reasons, and I haven't separated them. And these are throughput numbers: independent
reads overlap, so they understate the latency of a single miss. A pointer-chasing test would
measure latency directly.

It runs in the engineering workflow on GitHub's runners, and the output, including the machine's
cache sizes, is in each run's summary. It isn't a pass/fail check; timings vary by machine.
Built with an AI coding assistant, like the rest of this repository.
