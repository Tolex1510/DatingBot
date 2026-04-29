class Metrics:
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
        self.db_reads = 0
        self.db_writes = 0
        self.latencies: list[float] = []

    def hit(self):
        self.cache_hits += 1

    def miss(self):
        self.cache_misses += 1

    def db_read(self):
        self.db_reads += 1

    def db_write(self):
        self.db_writes += 1

    def record(self, ms: float):
        self.latencies.append(ms)

    def summary(self, duration_s: float) -> dict:
        n = len(self.latencies)
        total_cache_ops = self.cache_hits + self.cache_misses
        return {
            "throughput": round(n / duration_s, 2),
            "avg_latency_ms": round(sum(self.latencies) / n, 3) if n else 0.0,
            "db_hits": self.db_reads + self.db_writes,
            "cache_hit_rate": round(self.cache_hits / total_cache_ops, 4) if total_cache_ops else 0.0,
            "total_ops": n,
        }
