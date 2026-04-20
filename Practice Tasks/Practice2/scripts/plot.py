import csv
import os
import sys
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS_DIR = os.environ.get("RESULTS_DIR", "/results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")


def load_rows(path: str) -> list[dict]:
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def _num(r: dict, k: str) -> float:
    try:
        return float(r[k])
    except (TypeError, ValueError):
        return 0.0


def plot_throughput_vs_size(rows: list[dict]) -> None:
    # x = msg_size, y = received_per_sec, линии по broker, одна линия на rate (фасет через subplot)
    rates = sorted({int(r["target_rate"]) for r in rows})
    brokers = sorted({r["broker"] for r in rows})
    sizes = sorted({int(r["msg_size"]) for r in rows})

    fig, axes = plt.subplots(1, len(rates), figsize=(5 * len(rates), 4), sharey=True)
    if len(rates) == 1:
        axes = [axes]

    for ax, rate in zip(axes, rates):
        for broker in brokers:
            ys = []
            for size in sizes:
                match = [r for r in rows if r["broker"] == broker and int(r["msg_size"]) == size and int(r["target_rate"]) == rate]
                ys.append(_num(match[0], "received_per_sec") if match else 0)
            ax.plot(sizes, ys, marker="o", label=broker)
        ax.set_xscale("log")
        ax.set_xlabel("Msg size (bytes)")
        ax.set_title(f"rate={rate}/s")
        ax.grid(True, alpha=0.3)
        ax.legend()
    axes[0].set_ylabel("Received msg/sec")
    fig.suptitle("Throughput vs message size")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "throughput_vs_size.png"), dpi=120)
    plt.close(fig)


def plot_latency_p95_vs_rate(rows: list[dict]) -> None:
    sizes = sorted({int(r["msg_size"]) for r in rows})
    brokers = sorted({r["broker"] for r in rows})
    rates = sorted({int(r["target_rate"]) for r in rows})

    fig, axes = plt.subplots(1, len(sizes), figsize=(4 * len(sizes), 4), sharey=True)
    if len(sizes) == 1:
        axes = [axes]

    for ax, size in zip(axes, sizes):
        for broker in brokers:
            ys = []
            for rate in rates:
                match = [r for r in rows if r["broker"] == broker and int(r["msg_size"]) == size and int(r["target_rate"]) == rate]
                ys.append(_num(match[0], "p95_ms") if match else 0)
            ax.plot(rates, ys, marker="o", label=broker)
        ax.set_xlabel("Target rate (msg/s)")
        ax.set_title(f"size={size}B")
        ax.grid(True, alpha=0.3)
        ax.legend()
    axes[0].set_ylabel("p95 latency (ms)")
    fig.suptitle("p95 latency vs rate")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "latency_p95_vs_rate.png"), dpi=120)
    plt.close(fig)


def plot_loss_vs_rate(rows: list[dict]) -> None:
    sizes = sorted({int(r["msg_size"]) for r in rows})
    brokers = sorted({r["broker"] for r in rows})
    rates = sorted({int(r["target_rate"]) for r in rows})

    fig, axes = plt.subplots(1, len(sizes), figsize=(4 * len(sizes), 4), sharey=True)
    if len(sizes) == 1:
        axes = [axes]

    for ax, size in zip(axes, sizes):
        for broker in brokers:
            ys = []
            for rate in rates:
                match = [r for r in rows if r["broker"] == broker and int(r["msg_size"]) == size and int(r["target_rate"]) == rate]
                if not match:
                    ys.append(0)
                    continue
                sent = _num(match[0], "sent")
                lost = _num(match[0], "lost")
                ys.append(100.0 * lost / sent if sent else 0)
            ax.plot(rates, ys, marker="o", label=broker)
        ax.set_xlabel("Target rate (msg/s)")
        ax.set_title(f"size={size}B")
        ax.grid(True, alpha=0.3)
        ax.legend()
    axes[0].set_ylabel("Lost (%)")
    fig.suptitle("Message loss vs rate")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "loss_vs_rate.png"), dpi=120)
    plt.close(fig)


def main() -> None:
    csv_path = os.path.join(RESULTS_DIR, "raw.csv")
    if not os.path.exists(csv_path):
        print(f"no csv at {csv_path}", file=sys.stderr)
        sys.exit(1)
    os.makedirs(PLOTS_DIR, exist_ok=True)
    rows = load_rows(csv_path)
    plot_throughput_vs_size(rows)
    plot_latency_p95_vs_rate(rows)
    plot_loss_vs_rate(rows)
    print(f"plots saved to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
