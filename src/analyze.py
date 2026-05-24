#!/usr/bin/env python3
"""Analyze MPLADS spending data.

Reads from CSV files (preferred) or cache and computes:
- Pooled totals and rates by tenure
- Per-MP averages and medians
- Distributions
- Top/bottom performers
- Competitiveness analysis (when election data available)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

MPLADS_FILES = {
    "18th Lok Sabha": "mplads_18ls.csv",
    "17th Lok Sabha": "mplads_17ls.csv",
    "Rajya Sabha 18": "mplads_rs18.csv",
    "Rajya Sabha 17": "mplads_rs17.csv",
}

ELECTION_FILES = {
    "18th Lok Sabha": "elections_18ls.csv",
    "17th Lok Sabha": "elections_17ls.csv",
}


def normalize_constituency(name: str) -> str:
    """Normalize constituency name for matching."""
    s = str(name).upper().strip()
    s = re.sub(r"\s*\((SC|ST|GEN)\)\s*$", "", s)
    s = re.sub(r"\s+", " ", s)
    s = s.replace("&", "AND")
    s = s.replace("-", " ")
    s = re.sub(r"_[A-Z]{2}$", "", s)
    s = re.sub(r"\s+", " ", s).strip()

    replacements = {
        "ANANTHAPUR": "ANANTAPUR",
        "KURNOOLU": "KURNOOL",
        "NARSAPURAM": "NARASAPURAM",
        "NARSARAOPET": "NARASARAOPET",
        "THIRUPATHI": "TIRUPATI",
        "NAGAON": "NOWGONG",
        "PATLIPUTRA": "PATALIPUTRA",
        "PURNIA": "PURNEA",
        "UJIARPUR": "UJJARPUR",
        "SURGUJA": "SARGUJA",
        "SONIPAT": "SONEPAT",
        "PALAMU": "PALAMAU",
        "CHIKKABALLAPUR": "CHIKBALLAPUR",
        "CHAMARAJANAGAR": "CHAMRAJANAGAR",
        "ANANTNAG RAJOURI": "ANANTNAG",
        "BARAMULLA": "BARAMULLAH",
        "GADCHIROLI   CHIMUR": "GADCHIROLI CHIMUR",
        "HATKANANGALE": "HATKANANGLE",
        "RATNAGIRI  SINDHUDURG": "RATNAGIRI SINDHUDURG",
        "RATNAGIRI SINDHUDURG": "RATNAGIRI SINDHUDURG",
        "YAVATMAL  WASHIM": "YAVATMAL WASHIM",
        "BATHINDA": "BHATINDA",
        "DHARMAPURI": "DHARAMAPURI",
        "CHEVELLA": "CHELVELLA",
        "MAHBUBNAGAR": "MAHABUBNAGAR",
        "WARANGAL": "WARANGEL",
        "DADAR AND NAGAR HAVELI": "DADRA AND NAGAR HAVELI",
        "BAHARAICH": "BAHRAICH",
        "HARIDWAR": "HARDWAR",
        "NAINITAL UDHAMSINGH NAGAR": "NAINITAL UDHAM SINGH NAG.",
        "ARAMBAGH": "ARAMBAG",
        "SRERAMPUR": "SREERAMPUR",
        "ARUKU": "ARAKU",
        "CHANDINI CHOWK": "CHANDNI CHOWK",
        "CHIKKBALLAPUR": "CHIKBALLAPUR",
        "GUWAHATI": "GAUHATI",
        "DARRANG UDALGURI": "MANGALDOI",
        "DIPHU": "AUTONOMOUS DISTRICT",
        "KAZIRANGA": "KALIABOR",
        "SONITPUR": "TEZPUR",
        "BHANDARA GONDIYA": "BHANDARA GONDIYA",
        "AHMEDNAGAR": "AHMADNAGAR",
        "ANAKAPALLE": "ANAKAPALLI",
    }
    return replacements.get(s, s)


def normalize_state(name: str) -> str:
    """Normalize state name for matching."""
    s = str(name).upper().strip()
    s = s.replace("&", "AND")
    replacements = {
        "NCT OF DELHI": "DELHI",
        "THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    }
    return replacements.get(s, s)


def load_mplads(data_dir: Path, aggregate_file: str | None = None) -> pd.DataFrame:
    """Load MPLADS data from CSV files.

    If aggregate_file is provided, loads from that single file.
    Otherwise, loads from individual tenure files.
    """
    if aggregate_file:
        path = data_dir / aggregate_file
        if path.exists():
            df = pd.read_csv(path)
            df = df.rename(
                columns={
                    "allocated_cr": "allocated",
                    "recommended_cr": "recommended",
                    "sanctioned_cr": "sanctioned",
                    "completed_cr": "completed",
                    "tenure_label": "tenure",
                }
            )
            print(f"Loaded {len(df)} MPs from {aggregate_file}")
            df = df[df["allocated"] > 0].copy()
            return df
        print(f"Aggregate file {aggregate_file} not found, falling back to individual files")

    dfs = []
    for tenure, filename in MPLADS_FILES.items():
        path = data_dir / filename
        if path.exists():
            df = pd.read_csv(path)
            df["tenure"] = tenure
            df = df.rename(
                columns={
                    "allocated_cr": "allocated",
                    "recommended_cr": "recommended",
                    "sanctioned_cr": "sanctioned",
                    "completed_cr": "completed",
                }
            )
            dfs.append(df)
            print(f"Loaded {len(df)} MPs from {filename}")

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df = df[df["allocated"] > 0].copy()
    return df


def load_elections(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Load election data by tenure."""
    elections = {}
    for tenure, filename in ELECTION_FILES.items():
        path = data_dir / "elections" / filename
        if path.exists():
            df = pd.read_csv(path)
            df["const_norm"] = df["constituency"].apply(normalize_constituency)
            df["state_norm"] = df["state"].apply(normalize_state)
            elections[tenure] = df
    return elections


def merge_elections(
    mplads: pd.DataFrame, elections: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Merge election competitiveness data into MPLADS data."""
    mplads = mplads.copy()

    mplads["margin_pct"] = np.nan
    mplads["winner_party"] = None
    mplads["competitiveness"] = None

    for tenure, elec_df in elections.items():
        tenure_mask = mplads["tenure"] == tenure
        if not tenure_mask.any():
            continue

        elec_lookup = {}
        for _, row in elec_df.iterrows():
            key = (row["state_norm"], row["const_norm"])
            elec_lookup[key] = row

        for idx in mplads[tenure_mask].index:
            state = normalize_state(str(mplads.loc[idx, "state_name"]))
            const = normalize_constituency(str(mplads.loc[idx, "constituency_name"]))
            key = (state, const)

            if key in elec_lookup:
                elec = elec_lookup[key]
                mplads.loc[idx, "margin_pct"] = elec["margin_pct"]
                mplads.loc[idx, "winner_party"] = elec["winner_party"]
                mplads.loc[idx, "competitiveness"] = elec["competitiveness"]

    return mplads


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-MP rate columns."""
    df = df.copy()
    df["rec_pct"] = 100 * df["recommended"] / df["allocated"]
    df["sanc_pct"] = 100 * df["sanctioned"] / df["allocated"]
    df["comp_pct"] = 100 * df["completed"] / df["allocated"]
    df["sanc_yield"] = 100 * df["sanctioned"] / df["recommended"].replace(0, np.nan)
    df["comp_yield"] = 100 * df["completed"] / df["sanctioned"].replace(0, np.nan)
    return df


def print_tenure_summary(df: pd.DataFrame, tenure: str) -> None:
    """Print summary for one tenure."""
    n = len(df)
    alloc = df["allocated"].sum()
    rec = df["recommended"].sum()
    sanc = df["sanctioned"].sum()
    comp = df["completed"].sum()

    rec_pct = 100 * rec / alloc if alloc > 0 else 0
    sanc_pct = 100 * sanc / alloc if alloc > 0 else 0
    comp_pct = 100 * comp / alloc if alloc > 0 else 0

    print(f"\n{tenure} ({n} MPs):")
    print(f"  Allocated:   Rs {alloc:,.0f} Cr")
    print(f"  Recommended: Rs {rec:,.0f} Cr ({rec_pct:.0f}%)")
    print(f"  Sanctioned:  Rs {sanc:,.0f} Cr ({sanc_pct:.0f}%)")
    print(f"  Completed:   Rs {comp:,.0f} Cr ({comp_pct:.0f}%)")
    print(f"  Median completion: {df['comp_pct'].median():.1f}%")
    print(
        f"  Zero completion: {(df['completed'] == 0).sum()} MPs "
        f"({100*(df['completed']==0).mean():.0f}%)"
    )


def print_competitiveness_analysis(df: pd.DataFrame) -> None:
    """Print competitiveness analysis (Lok Sabha only)."""
    ls_tenures = [t for t in df["tenure"].unique() if "Lok Sabha" in str(t)]
    ls_df = df[df["tenure"].isin(ls_tenures)]

    if ls_df.empty:
        print("\n(No Lok Sabha data for competitiveness analysis)")
        return

    if "competitiveness" not in ls_df.columns or ls_df["competitiveness"].isna().all():
        print("\n(Election data not available for competitiveness analysis)")
        return

    print("\n" + "-" * 65)
    print("COMPETITIVENESS ANALYSIS (Lok Sabha only)")
    print("-" * 65)

    for tenure in ls_tenures:
        subset = df[(df["tenure"] == tenure) & df["competitiveness"].notna()]
        if subset.empty:
            continue

        print(f"\n{tenure}:")
        print(f"  Matched: {len(subset)} constituencies")

        comp_stats = subset.groupby("competitiveness").agg(
            n=("comp_pct", "count"),
            mean_completion=("comp_pct", "mean"),
            median_completion=("comp_pct", "median"),
            mean_rec=("rec_pct", "mean"),
        )

        print(
            f"\n  {'Category':<12} {'N':>5} {'Mean Comp%':>12} "
            f"{'Med Comp%':>11} {'Mean Rec%':>11}"
        )
        print(f"  {'-'*52}")
        for cat in ["safe", "competitive", "marginal"]:
            if cat in comp_stats.index:
                row = comp_stats.loc[cat]
                print(
                    f"  {cat:<12} {int(row['n']):>5} {row['mean_completion']:>11.1f}% "
                    f"{row['median_completion']:>10.1f}% {row['mean_rec']:>10.1f}%"
                )

        if subset["margin_pct"].notna().sum() > 10:
            corr = subset[["margin_pct", "comp_pct"]].dropna()
            if len(corr) > 2:
                r = corr["margin_pct"].corr(corr["comp_pct"])
                print(f"\n  Correlation (margin% vs completion%): {r:.3f}")

    print("\n" + "-" * 65)
    print("PARTY-WISE COMPLETION (Lok Sabha only)")
    print("-" * 65)

    for tenure in ls_tenures:
        subset = df[(df["tenure"] == tenure) & df["winner_party"].notna()]
        if subset.empty:
            continue

        print(f"\n{tenure}:")
        party_stats = (
            subset.groupby("winner_party")
            .agg(
                n=("comp_pct", "count"),
                mean_completion=("comp_pct", "mean"),
                median_completion=("comp_pct", "median"),
            )
            .sort_values("n", ascending=False)
        )

        print(f"  {'Party':<45} {'N':>5} {'Mean':>8} {'Median':>8}")
        print(f"  {'-'*68}")
        for party in party_stats.head(10).index:
            row = party_stats.loc[party]
            name = str(party)[:44]
            print(
                f"  {name:<45} {int(row['n']):>5} {row['mean_completion']:>7.1f}% "
                f"{row['median_completion']:>7.1f}%"
            )


def print_report(df: pd.DataFrame) -> None:
    """Print full analysis report."""
    print("=" * 65)
    print("MPLADS SPENDING ANALYSIS")
    print("=" * 65)

    print("\n" + "-" * 65)
    print("BY TENURE:")
    print("-" * 65)

    for tenure in df["tenure"].unique():
        subset = df[df["tenure"] == tenure]
        print_tenure_summary(subset, tenure)

    print("\n" + "-" * 65)
    print("COMBINED:")
    print("-" * 65)

    n = len(df)
    alloc = df["allocated"].sum()
    rec = df["recommended"].sum()
    sanc = df["sanctioned"].sum()
    comp = df["completed"].sum()

    print(
        f"""
Total MPs: {n}
  Allocated:   Rs {alloc:,.0f} Cr
  Recommended: Rs {rec:,.0f} Cr
  Sanctioned:  Rs {sanc:,.0f} Cr
  Completed:   Rs {comp:,.0f} Cr
"""
    )

    print("-" * 65)
    print(
        f"{'TENURE':<20} {'MPs':>6} {'ALLOC':>10} {'REC %':>8} {'COMP %':>8} {'MEDIAN':>8}"
    )
    print("-" * 65)

    for tenure in df["tenure"].unique():
        subset = df[df["tenure"] == tenure]
        n_t = len(subset)
        alloc_t = subset["allocated"].sum()
        rec_pct = 100 * subset["recommended"].sum() / alloc_t
        comp_pct = 100 * subset["completed"].sum() / alloc_t
        median = subset["comp_pct"].median()
        print(
            f"{tenure:<20} {n_t:>6} {alloc_t:>9.0f}Cr {rec_pct:>7.0f}% "
            f"{comp_pct:>7.1f}% {median:>7.1f}%"
        )

    print("-" * 65)

    print(
        f"""
OVERALL METRICS:
  Pooled completion:     {100 * comp / alloc:.1f}%
  Per-MP mean:           {df['comp_pct'].mean():.1f}%
  Per-MP median:         {df['comp_pct'].median():.1f}%
"""
    )

    print("COMPLETION RATE DISTRIBUTION (all tenures):")
    for p in [0, 10, 25, 50, 75, 90, 100]:
        val = df["comp_pct"].quantile(p / 100)
        bar = "#" * int(val / 2)
        print(f"  {p:3}th pctl: {val:5.1f}% {bar}")

    print(
        f"""
COMPLETION BUCKETS:
  Zero completion:  {(df['completed'] == 0).sum():3} MPs ({100 * (df['completed'] == 0).mean():.0f}%)
  0-10%:            {((df['comp_pct'] > 0) & (df['comp_pct'] < 10)).sum():3} MPs
  10-25%:           {((df['comp_pct'] >= 10) & (df['comp_pct'] < 25)).sum():3} MPs
  25-50%:           {((df['comp_pct'] >= 25) & (df['comp_pct'] < 50)).sum():3} MPs
  >50%:             {(df['comp_pct'] >= 50).sum():3} MPs
"""
    )

    print(
        f"""WORKS:
  Recommended: {df['n_recommended'].sum():,}
  Sanctioned:  {df['n_sanctioned'].sum():,}
  Completed:   {df['n_completed'].sum():,}
"""
    )

    print("TOP 3 BY COMPLETION % (per tenure):")
    for tenure in df["tenure"].unique():
        subset = df[df["tenure"] == tenure]
        top = subset.nlargest(3, "comp_pct")
        print(f"  {tenure}:")
        for _, r in top.iterrows():
            mp_name = r.get("mp_name", r.get("mp_id", "Unknown"))
            const = r.get("constituency_name", "")
            print(f"    {mp_name} ({const}): {r['comp_pct']:.0f}%")

    print_competitiveness_analysis(df)

    print("\n" + "=" * 65)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--aggregate", default=None, help="Use consolidated aggregate file")
    ap.add_argument("--out", help="Save per-MP data to CSV")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)

    df = load_mplads(data_dir, args.aggregate)
    if df.empty:
        print("No data found. Run fetch_mplads.py first and export to CSV.")
        return

    elections = load_elections(data_dir)
    if elections:
        print(f"Loaded election data for: {', '.join(elections.keys())}")
        df = merge_elections(df, elections)
        matched = df["competitiveness"].notna().sum()
        print(f"Matched {matched} MPs with election data")

    df = compute_metrics(df)
    print()
    print_report(df)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"\nSaved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
