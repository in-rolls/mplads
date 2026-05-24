#!/usr/bin/env python3
"""Analyze MPLADS spending data.

Reads from cache (works with partial data) and computes:
- Pooled totals and rates
- Per-MP averages and medians
- Distributions
- Top/bottom performers
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_amount(raw: str | None) -> float:
    """Parse amount string to crores."""
    if not raw:
        return 0.0
    s = str(raw).replace(",", "").replace("₹", "").strip()
    for unit in ("Cr", "cr", "Crore"):
        if s.endswith(unit):
            try:
                return float(s[: -len(unit)].strip())
            except ValueError:
                return 0.0
    try:
        v = float(s)
        return v / 1e7 if v > 100 else v
    except ValueError:
        return 0.0


def load_from_cache(cache_path: Path) -> pd.DataFrame:
    """Load MP data from JSONL cache."""
    data = []
    with cache_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            key = rec["key"]
            if not key.startswith("tiles|"):
                continue

            parts = key.split("|")
            state_id, const_id, mp_id = parts[1], parts[2], parts[3]
            tiles = rec["value"]

            row = {"mp_id": mp_id, "state_id": state_id, "const_id": const_id}
            for label, vals in tiles.items():
                if not isinstance(vals, list) or not vals:
                    continue
                if "Allocated" in label:
                    row["allocated"] = parse_amount(vals[-1])
                elif "Recommended" in label:
                    row["recommended"] = parse_amount(vals[-1])
                    row["n_recommended"] = int(vals[0]) if str(vals[0]).isdigit() else 0
                elif "Sanctioned" in label:
                    row["sanctioned"] = parse_amount(vals[-1])
                    row["n_sanctioned"] = int(vals[0]) if str(vals[0]).isdigit() else 0
                elif "Completed" in label:
                    row["completed"] = parse_amount(vals[-1])
                    row["n_completed"] = int(vals[0]) if str(vals[0]).isdigit() else 0
            data.append(row)

    df = pd.DataFrame(data)
    result: pd.DataFrame = df[df["allocated"] > 0].copy()
    return result


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-MP rate columns."""
    df = df.copy()
    df["rec_pct"] = 100 * df["recommended"] / df["allocated"]
    df["sanc_pct"] = 100 * df["sanctioned"] / df["allocated"]
    df["comp_pct"] = 100 * df["completed"] / df["allocated"]
    df["sanc_yield"] = 100 * df["sanctioned"] / df["recommended"].replace(0, np.nan)
    df["comp_yield"] = 100 * df["completed"] / df["sanctioned"].replace(0, np.nan)
    return df


def print_report(df: pd.DataFrame) -> None:
    """Print analysis report."""
    n = len(df)
    print("=" * 65)
    print(f"MPLADS SPENDING ANALYSIS ({n} MPs, 18th Lok Sabha)")
    print("=" * 65)

    # Totals
    alloc = df["allocated"].sum()
    rec = df["recommended"].sum()
    sanc = df["sanctioned"].sum()
    comp = df["completed"].sum()

    print(
        f"""
TOTALS:
  Allocated:   ₹{alloc:,.0f} Cr
  Recommended: ₹{rec:,.0f} Cr
  Sanctioned:  ₹{sanc:,.0f} Cr
  Completed:   ₹{comp:,.0f} Cr
"""
    )

    # Pooled vs Per-MP
    print("-" * 65)
    print(f"{'METRIC':<25} {'POOLED':>12} {'PER-MP MEAN':>12} {'MEDIAN':>12}")
    print("-" * 65)

    metrics = [
        ("Recommendation %", rec / alloc, df["rec_pct"].mean(), df["rec_pct"].median()),
        ("Sanction %", sanc / alloc, df["sanc_pct"].mean(), df["sanc_pct"].median()),
        ("Completion %", comp / alloc, df["comp_pct"].mean(), df["comp_pct"].median()),
    ]
    for name, pooled, mean, median in metrics:
        print(f"{name:<25} {100 * pooled:>11.1f}% {mean:>11.1f}% {median:>11.1f}%")

    print("-" * 65)

    # Conversion yields
    print(
        f"""
CONVERSION YIELDS (per-MP average):
  Recommended → Sanctioned: {df["sanc_yield"].mean():.1f}%
  Sanctioned → Completed:   {df["comp_yield"].mean():.1f}%
"""
    )

    # Distribution
    print("COMPLETION RATE DISTRIBUTION:")
    for p in [0, 10, 25, 50, 75, 90, 100]:
        val = df["comp_pct"].quantile(p / 100)
        bar = "█" * int(val / 2)
        print(f"  {p:3}th pctl: {val:5.1f}% {bar}")

    # Buckets
    print(
        f"""
COMPLETION BUCKETS:
  Zero completion:  {(df["completed"] == 0).sum():3} MPs ({100 * (df["completed"] == 0).mean():.0f}%)
  0-10%:            {((df["comp_pct"] > 0) & (df["comp_pct"] < 10)).sum():3} MPs
  10-25%:           {((df["comp_pct"] >= 10) & (df["comp_pct"] < 25)).sum():3} MPs
  25-50%:           {((df["comp_pct"] >= 25) & (df["comp_pct"] < 50)).sum():3} MPs
  >50%:             {(df["comp_pct"] >= 50).sum():3} MPs
"""
    )

    # Works count
    print(
        f"""WORKS:
  Recommended: {df["n_recommended"].sum():,}
  Sanctioned:  {df["n_sanctioned"].sum():,}
  Completed:   {df["n_completed"].sum():,}
  Conversion:  {100 * df["n_completed"].sum() / df["n_recommended"].sum():.0f}%
"""
    )

    # Top performers
    print("TOP 5 BY COMPLETION %:")
    top = df.nlargest(5, "comp_pct")
    for _, r in top.iterrows():
        print(
            f"  MP {r['mp_id']}: ₹{r['completed']:.1f}/{r['allocated']:.1f} Cr ({r['comp_pct']:.0f}%)"
        )

    # Bottom performers (with allocation but zero completion)
    print("\nBOTTOM 5 (zero completion, most recommended):")
    bottom = df[df["completed"] == 0].nlargest(n=5, columns="recommended")
    for _, r in bottom.iterrows():
        print(
            f"  MP {r['mp_id']}: ₹{r['allocated']:.1f} Cr alloc, ₹{r['recommended']:.1f} Cr rec, ₹0 done"
        )

    print("\n" + "=" * 65)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data/raw/mplads_full_cache.jsonl")
    ap.add_argument("--out", help="Save per-MP data to CSV")
    args = ap.parse_args()

    cache_path = Path(args.cache)
    if not cache_path.exists():
        print(f"Cache not found: {cache_path}")
        print("Run: uv run python src/fetch_mplads.py")
        return

    df = load_from_cache(cache_path)
    if df.empty:
        print("No data in cache yet")
        return

    df = compute_metrics(df)
    print_report(df)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"\nSaved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
