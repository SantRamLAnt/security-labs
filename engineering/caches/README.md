# Measuring the memory hierarchy

`memory_hierarchy.py` measures the caches described in MIT 6.004, Chapter 14 (Caches and the
Memory Hierarchy), from Python with NumPy:

1. **Random reads** from arrays of 16 KiB to 512 MiB. The time per read climbs in steps as the
   array outgrows each cache level reported by `lscpu`. On GitHub's runner (32 MiB of L3) it was
   about 1 to 1.5 ns up to 4 MiB, 4.6 ns at 16 MiB, and about 8.5 ns from 64 MiB up, once nearly
   every read has to go to main memory.
2. **Strided reads** of a 256 MiB array. Up to a stride of 8 values (one 64-byte cache line),
   each step wastes more of every line fetched.

Two things I'd flag. The simple cache-line model says the time per value should level off past
a stride of 8. On GitHub's AMD EPYC runner it levels off from a stride of 16 (6.2, 6.8, 6.6 ns);
on an Intel Xeon it kept rising (4.8 ns at a stride of 8, 18.8 ns at 64). Prefetching that pulls
in neighboring lines, and memory pages, are the likely reasons, and I haven't worked out which. And these are throughput numbers: independent
reads overlap, so they understate the latency of a single miss. A pointer-chasing test would
measure latency directly.

It runs in the engineering workflow on GitHub's runners, and the output, including the machine's
cache sizes, is in each run's summary. It isn't a pass/fail check; timings vary by machine.
Built with an AI coding assistant, like the rest of this repository.
