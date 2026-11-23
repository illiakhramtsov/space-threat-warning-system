"""Generate Latency and RPS charts from Locust CSV history files (Lab 4 & 6)."""

import argparse
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Locust load test metrics")
    parser.add_argument("--csv-prefix", default="load_tests/results/run")
    parser.add_argument("--out-dir", default="load_tests/results")
    args = parser.parse_args()

    history_file = Path(f"{args.csv_prefix}_stats_history.csv")
    if not history_file.exists():
        raise FileNotFoundError(f"Locust history CSV not found: {history_file}")

    df = pd.read_csv(history_file)
    agg = df[df["Name"] == "Aggregated"].copy()
    if agg.empty:
        raise ValueError("No Aggregated rows found in stats history CSV.")

    agg["Elapsed_s"] = agg["Timestamp"] - agg["Timestamp"].iloc[0]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Chart 1: Throughput (RPS) & User Count
    fig, ax1 = plt.subplots(figsize=(10, 4.8), dpi=160)
    ax1.plot(
        agg["Elapsed_s"],
        agg["Requests/s"],
        color="#1F618D",
        linewidth=2,
        label="RPS (Requests/s)",
    )
    ax1.set_xlabel("Час тесту (секунди)")
    ax1.set_ylabel("RPS (запитів/сек)", color="#1F618D")
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2 = ax1.twinx()
    ax2.plot(
        agg["Elapsed_s"],
        agg["User Count"],
        color="#D35400",
        linestyle="--",
        linewidth=1.5,
        label="Virtual Users",
    )
    ax2.set_ylabel("Віртуальні користувачі (VUsers)", color="#D35400")
    plt.title("Динаміка пропускної здатності (RPS) та кількості VUsers")
    fig.tight_layout()
    plt.savefig(out_dir / "rps_chart.png")
    plt.close()

    # Chart 2: Response Time (Average & 95th Percentile)
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=160)
    if "Total Average Response Time" in agg.columns:
        ax.plot(
            agg["Elapsed_s"],
            agg["Total Average Response Time"],
            color="#2E86C1",
            linewidth=2,
            label="Average Latency (ms)",
        )
    if "95%" in agg.columns:
        ax.plot(
            agg["Elapsed_s"],
            agg["95%"],
            color="#C0392B",
            linewidth=2,
            label="95th Percentile Latency (ms)",
        )
    ax.set_xlabel("Час тесту (секунди)")
    ax.set_ylabel("Час відповіді (мс)")
    ax.set_title("Динаміка затримки відповідей (Avg & P95 Latency)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    plt.savefig(out_dir / "latency_chart.png")
    plt.close()

    print(f"Charts saved to {out_dir}/rps_chart.png and {out_dir}/latency_chart.png")


if __name__ == "__main__":
    main()
