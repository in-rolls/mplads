#!/usr/bin/env python3
"""Check MPLADS data completeness and report gaps.

Reads from:
  data/mplads_full.csv - main data from fetch_mplads.py
  data/raw/mplads_full_cache.jsonl - cache for what we've fetched
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/mplads_full.csv")
    ap.add_argument("--cache", default="data/raw/mplads_full_cache.jsonl")
    args = ap.parse_args()

    print("=" * 60)
    print("MPLADS DATA COMPLETENESS CHECK")
    print("=" * 60)
    print()

    if not Path(args.data).exists():
        print(f"No data file yet: {args.data}")
        print("Run: python src/fetch_mplads.py")
        return

    df = pd.read_csv(args.data)
    print(f"Total MPs in dataset: {len(df)}")
    print()

    print("=== By Tenure ===")
    tenure_col = "tenure_id" if "tenure_id" in df.columns else "tenure_label"
    by_tenure = df.groupby(tenure_col).agg(
        n_mps=("mp_id", "count"),
        n_states=("state_name", "nunique"),
        with_spending=("allocated_cr", lambda x: x.notna().sum()),
    )
    print(by_tenure.to_string())
    print()

    print("=== By State ===")
    by_state = (
        df.groupby("state_name")
        .agg(
            n_mps=("mp_id", "count"),
            avg_allocated=("allocated_cr", "mean"),
            avg_completed=("completed_cr", "mean"),
        )
        .sort_values(by="n_mps", ascending=False)
    )
    print(by_state.head(15).to_string())
    print()

    with_alloc = df["allocated_cr"].notna().sum()
    without_alloc = len(df) - with_alloc
    print(f"MPs with allocation data: {with_alloc}")
    print(f"MPs missing allocation data: {without_alloc}")
    print()

    if Path(args.cache).exists():
        states_fetched = set()
        tiles_fetched = 0
        with open(args.cache) as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                key = rec.get("key", "")
                if key.startswith("const|"):
                    states_fetched.add(key.split("|")[1])
                elif key.startswith("tiles|"):
                    tiles_fetched += 1
        print(f"States in cache: {len(states_fetched)}")
        print(f"Tile records in cache: {tiles_fetched}")
        print()

    print("=" * 60)
    print("EXPECTED TOTALS:")
    print("  - 18th Lok Sabha: 543 seats")
    print("  - 17th Lok Sabha: 543 seats")
    print("=" * 60)
    print()

    for t in df[tenure_col].unique():
        subset = df[df[tenure_col] == t]
        expected = 543
        collected = len(subset)
        pct = 100 * collected / expected
        print(f"{t}: {collected}/{expected} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
