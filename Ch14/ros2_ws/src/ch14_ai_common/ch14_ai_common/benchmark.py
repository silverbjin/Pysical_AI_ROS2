"""Model-only timings; caller controls device transfer and synchronization."""
import time
import numpy as np


def seeded_input():
    return np.random.default_rng(14).random((1, 3, 640, 640), dtype=np.float32)


def summarize(values):
    a = np.asarray(values, dtype=np.float64)
    if a.ndim != 1 or not a.size or not np.isfinite(a).all() or np.any(a < 0):
        raise ValueError('nonempty finite nonnegative timing samples required')
    p50, p95, p99 = np.percentile(a, [50, 95, 99])
    return dict(samples=int(a.size), mean_ms=float(a.mean()), p50_ms=float(p50),
                p95_ms=float(p95), p99_ms=float(p99), max_ms=float(a.max()),
                std_ms=float(a.std()))


def measure(forward, *, warmup=10, iterations=100, synchronize=lambda: None,
            clock=time.perf_counter_ns):
    if type(warmup) is not int or type(iterations) is not int or warmup < 10 or iterations < 1:
        raise ValueError('warmup >=10 and positive integer iterations required')
    for _ in range(warmup):
        forward()
    synchronize()
    values = []
    for _ in range(iterations):
        synchronize()
        start = clock()
        forward()
        synchronize()
        elapsed = (clock() - start) / 1e6
        values.append(elapsed)
    return values, summarize(values)
