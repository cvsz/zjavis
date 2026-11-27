"""JARVIS load / stress testing tool.

Runs concurrent HTTP requests against the JARVIS API to measure
throughput and latency. Uses only httpx (already a project dependency)
so no extra load-testing tooling is required.

Usage:
    # Start the API in one terminal:
    PYTHONPATH=src python3 -m uvicorn jarvis.api.main:create_app --factory --host 127.0.0.1 --port 8000

    # Run the load test in another:
    PYTHONPATH=src python3 scripts/load_test.py --url http://127.0.0.1:8000 --duration 30 --concurrency 20
"""

from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class Result:
    status_code: int
    duration: float
    error: str | None = None


@dataclass
class Aggregate:
    total: int = 0
    ok: int = 0
    failed: int = 0
    errors: dict[str, int] = field(default_factory=dict)
    status_counts: dict[int, int] = field(default_factory=dict)
    min_latency: float = float("inf")
    max_latency: float = 0.0
    total_latency: float = 0.0
    latencies: list[float] = field(default_factory=list)

    def add(self, r: Result) -> None:
        self.total += 1
        self.status_counts[r.status_code] = self.status_counts.get(r.status_code, 0) + 1
        self.total_latency += r.duration
        self.min_latency = min(self.min_latency, r.duration)
        self.max_latency = max(self.max_latency, r.duration)
        self.latencies.append(r.duration)
        if r.error:
            self.failed += 1
            self.errors[r.error] = self.errors.get(r.error, 0) + 1
        elif 200 <= r.status_code < 400:
            self.ok += 1
        else:
            self.failed += 1

    @property
    def avg_latency(self) -> float:
        return self.total_latency / self.total if self.total else 0.0

    @property
    def p50(self) -> float:
        return self._percentile(50)

    @property
    def p95(self) -> float:
        return self._percentile(95)

    @property
    def p99(self) -> float:
        return self._percentile(99)

    def _percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        k = (p / 100) * (len(s) - 1)
        f = int(k)
        c = min(f + 1, len(s) - 1)
        if f == c:
            return s[f]
        return s[f] + (s[c] - s[f]) * (k - f)

    @property
    def rps(self) -> float:
        return self.total / self.total_latency if self.total_latency else 0.0


async def _worker(
    client: httpx.AsyncClient,
    url: str,
    stop: asyncio.Event,
    agg: Aggregate,
    lock: asyncio.Lock,
    method: str = "GET",
) -> None:
    while not stop.is_set():
        start = time.monotonic()
        try:
            if method == "GET":
                resp = await client.get(url, timeout=5.0)
            else:
                resp = await client.post(url, json={}, timeout=5.0)
            duration = time.monotonic() - start
            r = Result(status_code=resp.status_code, duration=duration)
        except httpx.RequestError as exc:
            duration = time.monotonic() - start
            r = Result(status_code=0, duration=duration, error=type(exc).__name__)
        except Exception as exc:  # noqa: BLE001
            duration = time.monotonic() - start
            r = Result(status_code=0, duration=duration, error=str(exc)[:80])
        async with lock:
            agg.add(r)


async def run_load_test(
    url: str,
    *,
    duration: float,
    concurrency: int,
    method: str = "GET",
) -> Aggregate:
    agg = Aggregate()
    lock = asyncio.Lock()
    stop = asyncio.Event()

    limits = httpx.Limits(
        max_keepalive_connections=concurrency,
        max_connections=concurrency,
    )
    async with httpx.AsyncClient(limits=limits) as client:
        workers = [
            asyncio.create_task(_worker(client, url, stop, agg, lock, method))
            for _ in range(concurrency)
        ]
        await asyncio.sleep(duration)
        stop.set()
        await asyncio.gather(*workers)

    return agg


def print_report(agg: Aggregate, duration: float, concurrency: int, url: str) -> None:
    print("\n=== JARVIS Load Test Report ===")
    print(f"Target:        {url}")
    print(f"Duration:      {duration:.1f}s")
    print(f"Concurrency:   {concurrency}")
    print(f"Total req:     {agg.total}")
    print(f"OK (2xx):      {agg.ok}")
    print(f"Failed:        {agg.failed}")
    print(f"RPS:           {agg.rps:.1f}")
    print(f"Avg latency:   {agg.avg_latency * 1000:.1f} ms")
    print(f"Min latency:   {agg.min_latency * 1000:.1f} ms")
    print(f"Max latency:   {agg.max_latency * 1000:.1f} ms")
    print(f"p50 latency:   {agg.p50 * 1000:.1f} ms")
    print(f"p95 latency:   {agg.p95 * 1000:.1f} ms")
    print(f"p99 latency:   {agg.p99 * 1000:.1f} ms")
    if agg.status_counts:
        print(
            "Status codes:  "
            + ", ".join(f"{k}:{v}" for k, v in sorted(agg.status_counts.items()))
        )
    if agg.errors:
        print(
            "Errors:        "
            + ", ".join(f"{k}:{v}" for k, v in sorted(agg.errors.items()))
        )
    print("==============================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load test the JARVIS API")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/health",
        help="Target URL (default: http://127.0.0.1:8000/health)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Test duration in seconds (default: 30)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Number of concurrent clients (default: 20)",
    )
    parser.add_argument(
        "--method",
        choices=["GET", "POST"],
        default="GET",
        help="HTTP method (default: GET)",
    )
    args = parser.parse_args()

    agg = asyncio.run(
        run_load_test(
            args.url,
            duration=args.duration,
            concurrency=args.concurrency,
            method=args.method,
        )
    )
    print_report(agg, args.duration, args.concurrency, args.url)


if __name__ == "__main__":
    main()
