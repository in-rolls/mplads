#!/usr/bin/env python3
"""Descriptive statistics for MPLADS data across LS 17, LS 18, and Rajya Sabha."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

DATA_DIR = Path(__file__).parent.parent / "data"
SOURCES = ["LS 17 (2014-19)", "LS 18 (2019-24)", "Rajya Sabha"]
STAGES = ["allocated_cr", "recommended_cr", "sanctioned_cr", "completed_cr"]
STAGE_LABELS = ["Allocated", "Recommended", "Sanctioned", "Completed"]


def load_data() -> pd.DataFrame:
    """Load and combine all MPLADS data."""
    ls18 = pd.read_csv(DATA_DIR / "mplads_18ls.csv")
    ls17 = pd.read_csv(DATA_DIR / "mplads_17ls.csv")
    rs = pd.read_csv(DATA_DIR / "mplads_rs.csv")

    ls18["source"] = "LS 18 (2019-24)"
    ls17["source"] = "LS 17 (2014-19)"
    rs["source"] = "Rajya Sabha"

    return pd.concat([ls18, ls17, rs], ignore_index=True)


def print_summary(df: pd.DataFrame) -> None:
    """Print summary statistics by source."""
    print("=" * 90)
    print("MPLADS DESCRIPTIVE STATISTICS")
    print("=" * 90)

    # Funnel: Allocated → Recommended → Sanctioned → Completed
    print("\n1. FUNDING FUNNEL (Rs. Crores, Totals)")
    print("-" * 90)
    print(f"{'Source':<20} {'N MPs':>8} {'Allocated':>12} {'Recommended':>12} {'Sanctioned':>12} {'Completed':>12}")
    print("-" * 90)
    for src in ["LS 17 (2014-19)", "LS 18 (2019-24)", "Rajya Sabha"]:
        s = df[df["source"] == src]
        print(f"{src:<20} {len(s):>8} {s['allocated_cr'].sum():>12.0f} {s['recommended_cr'].sum():>12.0f} {s['sanctioned_cr'].sum():>12.0f} {s['completed_cr'].sum():>12.0f}")

    print("\n2. FUNNEL CONVERSION RATES (% of Allocated)")
    print("-" * 90)
    print(f"{'Source':<20} {'Recommended %':>15} {'Sanctioned %':>15} {'Completed %':>15}")
    print("-" * 90)
    for src in ["LS 17 (2014-19)", "LS 18 (2019-24)", "Rajya Sabha"]:
        s = df[df["source"] == src]
        alloc = s["allocated_cr"].sum()
        rec_pct = s["recommended_cr"].sum() / alloc * 100
        sanc_pct = s["sanctioned_cr"].sum() / alloc * 100
        comp_pct = s["completed_cr"].sum() / alloc * 100
        print(f"{src:<20} {rec_pct:>14.1f}% {sanc_pct:>14.1f}% {comp_pct:>14.1f}%")

    print("\n3. STEP-BY-STEP CONVERSION RATES")
    print("-" * 90)
    print(f"{'Source':<20} {'Rec/Alloc':>12} {'Sanc/Rec':>12} {'Comp/Sanc':>12}")
    print("-" * 90)
    for src in ["LS 17 (2014-19)", "LS 18 (2019-24)", "Rajya Sabha"]:
        s = df[df["source"] == src]
        alloc = s["allocated_cr"].sum()
        rec = s["recommended_cr"].sum()
        sanc = s["sanctioned_cr"].sum()
        comp = s["completed_cr"].sum()
        rec_alloc = rec / alloc * 100
        sanc_rec = sanc / rec * 100 if rec > 0 else 0
        comp_sanc = comp / sanc * 100 if sanc > 0 else 0
        print(f"{src:<20} {rec_alloc:>11.1f}% {sanc_rec:>11.1f}% {comp_sanc:>11.1f}%")

    print("\n4. PER-MP AVERAGES (Rs. Crores)")
    print("-" * 90)
    print(f"{'Source':<20} {'Allocated':>12} {'Recommended':>12} {'Sanctioned':>12} {'Completed':>12}")
    print("-" * 90)
    for src in ["LS 17 (2014-19)", "LS 18 (2019-24)", "Rajya Sabha"]:
        s = df[df["source"] == src]
        print(f"{src:<20} {s['allocated_cr'].mean():>12.2f} {s['recommended_cr'].mean():>12.2f} {s['sanctioned_cr'].mean():>12.2f} {s['completed_cr'].mean():>12.2f}")

    print("\n5. WORK COUNTS (Totals)")
    print("-" * 90)
    print(f"{'Source':<20} {'Recommended':>15} {'Sanctioned':>15} {'Completed':>15}")
    print("-" * 90)
    for src in ["LS 17 (2014-19)", "LS 18 (2019-24)", "Rajya Sabha"]:
        s = df[df["source"] == src]
        print(f"{src:<20} {int(s['n_recommended'].sum()):>15,} {int(s['n_sanctioned'].sum()):>15,} {int(s['n_completed'].sum()):>15,}")

    print("\n6. ZERO ACTIVITY MPs")
    print("-" * 90)
    for src in ["LS 17 (2014-19)", "LS 18 (2019-24)", "Rajya Sabha"]:
        s = df[df["source"] == src]
        zero_rec = (s["recommended_cr"] == 0).sum()
        zero_comp = (s["completed_cr"] == 0).sum()
        print(f"{src}: {zero_rec} MPs with zero recommended ({zero_rec/len(s)*100:.1f}%), {zero_comp} with zero completed ({zero_comp/len(s)*100:.1f}%)")

    print("\n" + "=" * 90)


def plot_funnel(df: pd.DataFrame) -> None:
    """Create grouped bar chart showing funding funnel by source."""
    fig, ax = plt.subplots(figsize=(12, 6))

    funnel_data = []
    for src in SOURCES:
        s = df[df["source"] == src]
        funnel_data.append([s[stage].sum() for stage in STAGES])

    x = range(len(STAGE_LABELS))
    width = 0.25
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    for i, (src, data) in enumerate(zip(SOURCES, funnel_data)):
        offset = (i - 1) * width
        ax.bar([xi + offset for xi in x], data, width, label=src, color=colors[i])

    ax.set_xlabel("Stage")
    ax.set_ylabel("Amount (Rs. Crores)")
    ax.set_title("MPLADS Funding Funnel: Allocated → Completed")
    ax.set_xticks(x)
    ax.set_xticklabels(STAGE_LABELS)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(DATA_DIR / "descriptive_funnel.png", dpi=150)
    plt.close()
    print(f"Saved: {DATA_DIR / 'descriptive_funnel.png'}")


def plot_distributions(df: pd.DataFrame) -> None:
    """Plot completion rate distributions by source."""
    df = df.copy()
    df["completion_rate"] = df["completed_cr"] / df["allocated_cr"] * 100
    df["completion_rate"] = df["completion_rate"].fillna(0)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histograms
    ax = axes[0]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    for src, color in zip(SOURCES, colors):
        subset = df[df["source"] == src]["completion_rate"]
        ax.hist(subset, bins=20, alpha=0.5, label=src, color=color, edgecolor="black")
    ax.set_xlabel("Completion Rate (%)")
    ax.set_ylabel("Number of MPs")
    ax.set_title("Distribution of MP Completion Rates")
    ax.legend()
    ax.grid(alpha=0.3)

    # Box plots
    ax = axes[1]
    sns.boxplot(data=df, x="source", y="completion_rate", hue="source", ax=ax, palette=colors, legend=False)
    ax.set_xlabel("Source")
    ax.set_ylabel("Completion Rate (%)")
    ax.set_title("Completion Rate Comparison by Source")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(DATA_DIR / "descriptive_distributions.png", dpi=150)
    plt.close()
    print(f"Saved: {DATA_DIR / 'descriptive_distributions.png'}")


def plot_percentiles(df: pd.DataFrame) -> None:
    """Print percentile table and create violin plots for per-MP averages."""
    print("\n7. PER-MP PERCENTILES (Rs. Crores)")
    print("-" * 90)
    print(f"{'Source':<20} {'Stage':<12} {'Mean':>10} {'Median':>10} {'25th':>10} {'75th':>10}")
    print("-" * 90)

    for src in SOURCES:
        s = df[df["source"] == src]
        for stage, label in zip(STAGES, STAGE_LABELS):
            vals = s[stage]
            print(
                f"{src:<20} {label:<12} {vals.mean():>10.2f} {vals.median():>10.2f} "
                f"{vals.quantile(0.25):>10.2f} {vals.quantile(0.75):>10.2f}"
            )
        print("-" * 90)

    # Violin plots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    for i, (stage, label) in enumerate(zip(STAGES, STAGE_LABELS)):
        ax = axes[i]
        sns.violinplot(data=df, x="source", y=stage, hue="source", ax=ax, palette=colors, legend=False)
        ax.set_xlabel("Source")
        ax.set_ylabel(f"{label} (Rs. Crores)")
        ax.set_title(f"Per-MP {label} Distribution")
        ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(DATA_DIR / "descriptive_percentiles.png", dpi=150)
    plt.close()
    print(f"Saved: {DATA_DIR / 'descriptive_percentiles.png'}")


def plot_scatter(df: pd.DataFrame) -> None:
    """Scatter plot of recommended vs completed amounts by source."""
    fig, ax = plt.subplots(figsize=(10, 8))

    colors = {"LS 17 (2014-19)": "#1f77b4", "LS 18 (2019-24)": "#ff7f0e", "Rajya Sabha": "#2ca02c"}

    for src in SOURCES:
        subset = df[df["source"] == src]
        ax.scatter(
            subset["recommended_cr"],
            subset["completed_cr"],
            alpha=0.5,
            label=src,
            color=colors[src],
            s=30,
        )

    # Add diagonal reference line
    max_val = max(df["recommended_cr"].max(), df["completed_cr"].max())
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.3, label="1:1 line")

    ax.set_xlabel("Recommended (Rs. Crores)")
    ax.set_ylabel("Completed (Rs. Crores)")
    ax.set_title("MP Activity: Recommended vs Completed")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(DATA_DIR / "descriptive_scatter.png", dpi=150)
    plt.close()
    print(f"Saved: {DATA_DIR / 'descriptive_scatter.png'}")


def main() -> None:
    df = load_data()
    print_summary(df)
    plot_percentiles(df)

    print("\nGenerating visualizations...")
    plot_funnel(df)
    plot_distributions(df)
    plot_scatter(df)
    print("\nAll visualizations saved to data/ directory.")


if __name__ == "__main__":
    main()
