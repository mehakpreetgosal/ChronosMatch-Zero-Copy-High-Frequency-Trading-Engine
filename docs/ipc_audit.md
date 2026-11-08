# IPC Audit - Zero-Copy Architecture

* Orders sent between two separate Python processes: **1,000,000**
* Orders received intact and in order: **1,000,000** (corrupt / out of order: 0)
* Result: **PASS**

| Method | Orders/s | Producer CPU per order |
|---|---|---|
| mmap ring buffer (zero-copy, no pickling) | 994,097 | 0.84 us |
| multiprocessing.Queue (pickling) | 87,880 | 1.17 us |

Zero-copy is **11.3x faster** than the pickling baseline.
