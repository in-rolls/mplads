#!/usr/bin/env python3
"""Descriptive statistics for MPLADS data across LS 17, LS 18, and Rajya Sabha."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from _config import COLORS, SOURCES, STAGES, STAGE_LABELS

DATA_DIR = Path(__file__).parent.parent / "data"


def load_data() -> pd.DataFrame:
    """Load and combine all MPLADS data."""
    ls18 = pd.read_csv(DATA_DIR / "mplads_18ls.csv")
    ls17 = pd.read_csv(DATA_DIR / "mplads_17ls.csv")
    rs = pd.read_csv(DATA_DIR / "mplads_rs.csv")

    ls18["source"] = "LS 18 (2024-)"
    ls17["source"] = "LS 17 (2019-24)"
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
    for src in SOURCES:
        s = df[df["source"] == src]
        print(f"{src:<20} {len(s):>8} {s['allocated_cr'].sum():>12.0f} {s['recommended_cr'].sum():>12.0f} {s['sanctioned_cr'].sum():>12.0f} {s['completed_cr'].sum():>12.0f}")

    print("\n2. FUNNEL CONVERSION RATES (% of Allocated)")
    print("-" * 90)
    print(f"{'Source':<20} {'Recommended %':>15} {'Sanctioned %':>15} {'Completed %':>15}")
    print("-" * 90)
    for src in SOURCES:
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
    for src in SOURCES:
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
    for src in SOURCES:
        s = df[df["source"] == src]
        print(f"{src:<20} {s['allocated_cr'].mean():>12.2f} {s['recommended_cr'].mean():>12.2f} {s['sanctioned_cr'].mean():>12.2f} {s['completed_cr'].mean():>12.2f}")

    print("\n5. WORK COUNTS (Totals)")
    print("-" * 90)
    print(f"{'Source':<20} {'Recommended':>15} {'Sanctioned':>15} {'Completed':>15}")
    print("-" * 90)
    for src in SOURCES:
        s = df[df["source"] == src]
        print(f"{src:<20} {int(s['n_recommended'].sum()):>15,} {int(s['n_sanctioned'].sum()):>15,} {int(s['n_completed'].sum()):>15,}")

    print("\n6. ZERO ACTIVITY MPs")
    print("-" * 90)
    for src in SOURCES:
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

    for i, (src, data) in enumerate(zip(SOURCES, funnel_data)):
        offset = (i - 1) * width
        ax.bar([xi + offset for xi in x], data, width, label=src, color=COLORS[i])

    ax.set_xlabel("Stage")
    ax.set_ylabel("Amount (Rs. Crores)")
    ax.set_title("MPLADS Funding Funnel: Allocated → Completed")
    ax.set_xticks(x)
    ax.set_xticklabels(STAGE_LABELS)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(DATA_DIR / "fig_01_funnel.png", dpi=150)
    plt.close()
    print(f"Saved: {DATA_DIR / 'fig_01_funnel.png'}")


def plot_distributions(df: pd.DataFrame) -> None:
    """Plot completion rate distributions by source."""
    df = df.copy()
    df["completion_rate"] = df["completed_cr"] / df["allocated_cr"] * 100
    df["completion_rate"] = df["completion_rate"].fillna(0)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histograms
    ax = axes[0]
    for src, color in zip(SOURCES, COLORS):
        subset = df[df["source"] == src]["completion_rate"]
        ax.hist(subset, bins=20, alpha=0.5, label=src, color=color, edgecolor="black")
    ax.set_xlabel("Completion Rate (%)")
    ax.set_ylabel("Number of MPs")
    ax.set_title("Distribution of MP Completion Rates")
    ax.legend()
    ax.grid(alpha=0.3)

    # Box plots
    ax = axes[1]
    sns.boxplot(data=df, x="source", y="completion_rate", hue="source", ax=ax, palette=COLORS, legend=False)
    ax.set_xlabel("Source")
    ax.set_ylabel("Completion Rate (%)")
    ax.set_title("Completion Rate Comparison by Source")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(DATA_DIR / "fig_02_distributions.png", dpi=150)
    plt.close()
    print(f"Saved: {DATA_DIR / 'fig_02_distributions.png'}")


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

    for i, (stage, label) in enumerate(zip(STAGES, STAGE_LABELS)):
        ax = axes[i]
        sns.violinplot(data=df, x="source", y=stage, hue="source", ax=ax, palette=COLORS, legend=False)
        ax.set_xlabel("Source")
        ax.set_ylabel(f"{label} (Rs. Crores)")
        ax.set_title(f"Per-MP {label} Distribution")
        ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(DATA_DIR / "fig_03_percentiles.png", dpi=150)
    plt.close()
    print(f"Saved: {DATA_DIR / 'fig_03_percentiles.png'}")


def plot_scatter(df: pd.DataFrame) -> None:
    """Scatter plot of recommended vs completed amounts by source."""
    fig, ax = plt.subplots(figsize=(10, 8))

    color_map = dict(zip(SOURCES, COLORS))

    for src in SOURCES:
        subset = df[df["source"] == src]
        ax.scatter(
            subset["recommended_cr"],
            subset["completed_cr"],
            alpha=0.5,
            label=src,
            color=color_map[src],
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
    plt.savefig(DATA_DIR / "fig_04_scatter.png", dpi=150)
    plt.close()
    print(f"Saved: {DATA_DIR / 'fig_04_scatter.png'}")


def print_unspent_analysis(df: pd.DataFrame) -> None:
    """Q5: Analyze money left on the table at 17th LS transition."""
    print("\n" + "=" * 90)
    print("Q5: MONEY LEFT ON THE TABLE (17th Lok Sabha)")
    print("=" * 90)
    print("\nThis analysis focuses on 17th LS MPs at term end (2024).")
    print("'Unspent' = Allocated - Completed (funds allocated but never completed projects)")

    ls17 = df[df["source"] == "LS 17 (2019-24)"].copy()

    ls17["unspent_cr"] = ls17["allocated_cr"] - ls17["completed_cr"]
    ls17["unspent_pct"] = (ls17["unspent_cr"] / ls17["allocated_cr"] * 100).fillna(0)

    total_alloc = ls17["allocated_cr"].sum()
    total_comp = ls17["completed_cr"].sum()
    total_unspent = ls17["unspent_cr"].sum()

    print("\n1. TOTAL UNSPENT AT 17TH LS TRANSITION")
    print("-" * 60)
    print(f"  Total Allocated:  Rs {total_alloc:,.0f} Cr")
    print(f"  Total Completed:  Rs {total_comp:,.0f} Cr")
    print(f"  TOTAL UNSPENT:    Rs {total_unspent:,.0f} Cr ({total_unspent/total_alloc*100:.1f}%)")


def unspent_by_state(df: pd.DataFrame) -> None:
    """Show which states leave the most money unspent."""
    print("\n2. UNSPENT BY STATE (17th LS only)")
    print("-" * 90)

    ls17 = df[df["source"] == "LS 17 (2019-24)"].copy()
    ls17["unspent_cr"] = ls17["allocated_cr"] - ls17["completed_cr"]
    ls17["unspent_pct"] = (ls17["unspent_cr"] / ls17["allocated_cr"] * 100).fillna(0)

    state_stats = ls17.groupby("state_name").agg({
        "allocated_cr": "sum",
        "completed_cr": "sum",
        "unspent_cr": "sum",
        "mp_id": "count"
    }).reset_index()
    state_stats.columns = ["State", "Allocated", "Completed", "Unspent", "N_MPs"]
    state_stats["Unspent_Pct"] = state_stats["Unspent"] / state_stats["Allocated"] * 100
    state_stats = state_stats.sort_values("Unspent", ascending=False)

    print(f"{'State':<25} {'Allocated':>10} {'Completed':>10} {'Unspent':>10} {'Unspent%':>10} {'N MPs':>8}")
    print("-" * 90)
    for _, row in state_stats.head(15).iterrows():
        print(f"{row['State']:<25} {row['Allocated']:>10.1f} {row['Completed']:>10.1f} {row['Unspent']:>10.1f} {row['Unspent_Pct']:>9.1f}% {row['N_MPs']:>8}")


def unspent_by_party(df: pd.DataFrame) -> None:
    """Show party-level unspent patterns (requires election data merge)."""
    print("\n3. UNSPENT BY PARTY (17th LS, requires election data)")
    print("-" * 90)

    election_file = DATA_DIR / "mplads_election_merged.csv"
    if not election_file.exists():
        print("  Election data not found. Skipping party analysis.")
        return

    election_df = pd.read_csv(election_file)

    ls17 = df[df["source"] == "LS 17 (2019-24)"].copy()
    ls17["unspent_cr"] = ls17["allocated_cr"] - ls17["completed_cr"]

    merged = ls17.merge(
        election_df[["mp_id", "Party"]].drop_duplicates(),
        on="mp_id",
        how="left"
    )
    merged["Party"] = merged["Party"].fillna("Unknown")

    party_stats = merged.groupby("Party").agg({
        "allocated_cr": "sum",
        "completed_cr": "sum",
        "unspent_cr": "sum",
        "mp_id": "count"
    }).reset_index()
    party_stats.columns = ["Party", "Allocated", "Completed", "Unspent", "N_MPs"]
    party_stats["Unspent_Pct"] = party_stats["Unspent"] / party_stats["Allocated"] * 100
    party_stats = party_stats[party_stats["N_MPs"] >= 5].sort_values("Unspent", ascending=False)

    print(f"{'Party':<15} {'Allocated':>10} {'Completed':>10} {'Unspent':>10} {'Unspent%':>10} {'N MPs':>8}")
    print("-" * 90)
    for _, row in party_stats.head(15).iterrows():
        print(f"{row['Party']:<15} {row['Allocated']:>10.1f} {row['Completed']:>10.1f} {row['Unspent']:>10.1f} {row['Unspent_Pct']:>9.1f}% {row['N_MPs']:>8}")


def unspent_distribution(df: pd.DataFrame) -> None:
    """Show MP-level distribution of unspent funds in brackets."""
    print("\n4. UNSPENT DISTRIBUTION BY MP (17th LS)")
    print("-" * 60)

    ls17 = df[df["source"] == "LS 17 (2019-24)"].copy()
    ls17["unspent_cr"] = ls17["allocated_cr"] - ls17["completed_cr"]
    ls17["completion_pct"] = (ls17["completed_cr"] / ls17["allocated_cr"] * 100).fillna(0)

    brackets = [
        (">75% completed", ls17["completion_pct"] > 75),
        ("50-75% completed", (ls17["completion_pct"] > 50) & (ls17["completion_pct"] <= 75)),
        ("25-50% completed", (ls17["completion_pct"] > 25) & (ls17["completion_pct"] <= 50)),
        ("<25% completed", ls17["completion_pct"] <= 25),
    ]

    print(f"{'Bracket':<20} {'N MPs':>10} {'% of MPs':>10} {'Avg Unspent (Cr)':>18}")
    print("-" * 60)
    for label, mask in brackets:
        subset = ls17[mask]
        n = len(subset)
        pct = n / len(ls17) * 100
        avg_unspent = subset["unspent_cr"].mean() if n > 0 else 0
        print(f"{label:<20} {n:>10} {pct:>9.1f}% {avg_unspent:>18.2f}")

    print("\n  Summary:")
    print(f"  Median completion rate: {ls17['completion_pct'].median():.1f}%")
    print(f"  MPs with <50% completion: {(ls17['completion_pct'] < 50).sum()} ({(ls17['completion_pct'] < 50).mean()*100:.1f}%)")
    print(f"  MPs with 0% completion: {(ls17['completion_pct'] == 0).sum()} ({(ls17['completion_pct'] == 0).mean()*100:.1f}%)")


def turnover_analysis() -> None:
    """Q5b: MP Turnover and Unspent Money Analysis.

    Analyzes whether MPs who left office (turnover) left more money unspent
    compared to MPs who retained their seats.
    """
    from scipy import stats

    print("\n" + "=" * 90)
    print("Q5b: MP TURNOVER AND UNSPENT MONEY ANALYSIS")
    print("=" * 90)
    print("\nDid departing MPs leave more money on the table?")
    print("Turnover = different MP in LS18 vs LS17 for same constituency")

    ls17_raw = pd.read_csv(DATA_DIR / "mplads_17ls.csv")
    ls18_raw = pd.read_csv(DATA_DIR / "mplads_18ls.csv")

    ls17 = (
        ls17_raw.sort_values("allocated_cr", ascending=False)
        .drop_duplicates(subset=["state_name", "constituency_name"], keep="first")
        .copy()
    )
    ls18 = (
        ls18_raw.sort_values("allocated_cr", ascending=False)
        .drop_duplicates(subset=["state_name", "constituency_name"], keep="first")
        .copy()
    )

    n_ls17_unique = len(ls17)
    n_ls18_unique = len(ls18)

    wide = ls17.merge(
        ls18,
        on=["state_name", "constituency_name"],
        suffixes=("_LS17", "_LS18"),
        how="inner",
    )

    wide["turnover"] = wide["mp_id_LS17"] != wide["mp_id_LS18"]
    wide["unspent_LS17"] = wide["allocated_cr_LS17"] - wide["completed_cr_LS17"]
    wide["unspent_pct_LS17"] = (
        wide["unspent_LS17"] / wide["allocated_cr_LS17"] * 100
    ).fillna(0)
    wide["completion_pct_LS17"] = (
        wide["completed_cr_LS17"] / wide["allocated_cr_LS17"] * 100
    ).fillna(0)

    n_matched = len(wide)
    n_turnover = wide["turnover"].sum()
    n_retained = n_matched - n_turnover
    turnover_rate = n_turnover / n_matched * 100

    print("\n1. TURNOVER SUMMARY")
    print("-" * 60)
    print(f"  Unique constituencies in LS17: {n_ls17_unique}")
    print(f"  Unique constituencies in LS18: {n_ls18_unique}")
    print(f"  Matched constituencies: {n_matched}")
    print(f"  Unmatched (boundary changes etc.): {n_ls17_unique - n_matched}")
    print(f"\n  MP Turnover: {n_turnover} ({turnover_rate:.1f}%)")
    print(f"  MPs Retained: {n_retained} ({100 - turnover_rate:.1f}%)")

    print("\n2. UNSPENT BY TURNOVER STATUS (LS17 Term)")
    print("-" * 90)
    print(
        f"{'Turnover?':<12} {'N':>6} {'Mean Unspent':>14} {'Median Unspent':>16} "
        f"{'Total Unspent':>15} {'Mean Compl%':>12}"
    )
    print("-" * 90)

    for turnover_val, label in [(True, "Yes (Left)"), (False, "No (Stayed)")]:
        subset = wide[wide["turnover"] == turnover_val]
        n = len(subset)
        mean_unspent = subset["unspent_LS17"].mean()
        median_unspent = subset["unspent_LS17"].median()
        total_unspent = subset["unspent_LS17"].sum()
        mean_completion = subset["completion_pct_LS17"].mean()
        print(
            f"{label:<12} {n:>6} {mean_unspent:>13.2f} Cr {median_unspent:>14.2f} Cr "
            f"{total_unspent:>13.1f} Cr {mean_completion:>11.1f}%"
        )

    turnover_unspent = wide[wide["turnover"]]["unspent_LS17"].dropna()
    retained_unspent = wide[~wide["turnover"]]["unspent_LS17"].dropna()
    t_result = stats.ttest_ind(turnover_unspent, retained_unspent)
    u_result = stats.mannwhitneyu(
        turnover_unspent, retained_unspent, alternative="two-sided"
    )

    print("\n3. STATISTICAL TESTS")
    print("-" * 60)
    print(f"  T-test (unspent amounts): t={t_result.statistic:.3f}, p={t_result.pvalue:.4f}")
    print(f"  Mann-Whitney U test: U={u_result.statistic:.0f}, p={u_result.pvalue:.4f}")
    if t_result.pvalue < 0.05:
        print("  -> Statistically significant difference at p<0.05")
    else:
        print("  -> No statistically significant difference at p<0.05")

    turnover_total = wide[wide["turnover"]]["unspent_LS17"].sum()
    retained_total = wide[~wide["turnover"]]["unspent_LS17"].sum()

    print("\n4. THE 'WASTE' NARRATIVE")
    print("-" * 60)
    print(f"  Rs {turnover_total:.1f} Cr left unspent by departing MPs")
    print(f"  Rs {retained_total:.1f} Cr left unspent by retained MPs")
    print(f"  -> Departing MPs accounted for {turnover_total/(turnover_total+retained_total)*100:.1f}% of total unspent")
    print(
        f"\n  Interpretation: {n_turnover} constituencies now have new MPs who"
    )
    print("  may deprioritize predecessor's incomplete projects.")

    print("\n5. COMPLETION RATE COMPARISON")
    print("-" * 60)
    turnover_comp = wide[wide["turnover"]]["completion_pct_LS17"]
    retained_comp = wide[~wide["turnover"]]["completion_pct_LS17"]
    print(f"  Departing MPs avg completion: {turnover_comp.mean():.1f}%")
    print(f"  Retained MPs avg completion:  {retained_comp.mean():.1f}%")
    print(f"  Difference: {retained_comp.mean() - turnover_comp.mean():+.1f} percentage points")

    print("\n6. TURNOVER BY STATE (Top 10 by turnover count)")
    print("-" * 90)

    state_turnover = (
        wide.groupby("state_name")
        .agg(
            n_constituencies=("turnover", "count"),
            n_turnover=("turnover", "sum"),
        )
        .reset_index()
    )

    turnover_only = wide[wide["turnover"]]
    state_unspent = (
        turnover_only.groupby("state_name")["unspent_LS17"]
        .sum()
        .reset_index()
        .rename(columns={"unspent_LS17": "total_unspent_turnover"})
    )
    state_turnover = state_turnover.merge(state_unspent, on="state_name", how="left")
    state_turnover["total_unspent_turnover"] = state_turnover[
        "total_unspent_turnover"
    ].fillna(0)

    state_turnover["turnover_rate"] = (
        state_turnover["n_turnover"] / state_turnover["n_constituencies"] * 100
    )
    state_turnover = state_turnover.sort_values("n_turnover", ascending=False)

    print(
        f"{'State':<25} {'Seats':>6} {'Turnover':>10} {'Rate':>8} "
        f"{'Unspent by Departed':>20}"
    )
    print("-" * 90)
    for _, row in state_turnover.head(10).iterrows():
        print(
            f"{row['state_name']:<25} {int(row['n_constituencies']):>6} "
            f"{int(row['n_turnover']):>10} {row['turnover_rate']:>7.1f}% "
            f"{row['total_unspent_turnover']:>18.1f} Cr"
        )

    print("\n7. CAVEATS")
    print("-" * 60)
    print("  1. LS18 is early in term - unspent will be high for all LS18 MPs")
    print("  2. LS17 analysis is more meaningful (full 5-year term)")
    print("  3. Causality unclear: poor delivery may CAUSE defeat (reverse causation)")
    print(f"  4. {len(ls17) - n_matched} constituencies unmatchable due to boundary changes")


def main() -> None:
    df = load_data()
    print_summary(df)
    plot_percentiles(df)

    print("\nGenerating visualizations...")
    plot_funnel(df)
    plot_distributions(df)
    plot_scatter(df)
    print("\nAll visualizations saved to data/ directory.")

    print_unspent_analysis(df)
    unspent_by_state(df)
    unspent_by_party(df)
    unspent_distribution(df)
    turnover_analysis()


if __name__ == "__main__":
    main()
