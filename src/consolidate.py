#!/usr/bin/env python3
"""Consolidate MPLADS data files into unified outputs.

Creates:
  data/mplads_aggregate.csv - One row per MP-tenure with spending totals
  data/mplads_works.csv     - One row per work/project
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

AGGREGATE_FILES = {
    "18th Lok Sabha": "mplads_18ls.csv",
    "17th Lok Sabha": "mplads_17ls.csv",
    "Rajya Sabha": "mplads_rs.csv",
}

WORKS_FILES = {
    "18th Lok Sabha": "works_ls18.csv",
    "17th Lok Sabha": "works_ls17.csv",
    "Rajya Sabha": "works_rs.csv",
}


def consolidate_aggregate(data_dir: Path, output_path: Path) -> None:
    """Combine aggregate MP spending files into one."""
    dfs = []
    for tenure, filename in AGGREGATE_FILES.items():
        path = data_dir / filename
        if path.exists():
            df = pd.read_csv(path)
            df["tenure_label"] = tenure
            dfs.append(df)
            print(f"  {filename}: {len(df)} rows")
        else:
            print(f"  {filename}: NOT FOUND")

    if not dfs:
        print("No aggregate files found")
        return

    combined = pd.concat(dfs, ignore_index=True)

    key_cols = ["mp_id", "tenure_label"]
    dups = combined.duplicated(subset=key_cols, keep=False)
    if dups.any():
        print(f"  WARNING: {dups.sum()} duplicate rows by {key_cols}")
        combined = combined.drop_duplicates(subset=key_cols, keep="first")
        print(f"  Kept first occurrence, now {len(combined)} rows")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)
    print(f"  -> {output_path}: {len(combined)} rows")


def consolidate_works(data_dir: Path, output_path: Path) -> None:
    """Combine works detail files into one."""
    dfs = []
    for tenure, filename in WORKS_FILES.items():
        path = data_dir / filename
        if path.exists():
            df = pd.read_csv(path)
            df["tenure_label"] = tenure
            dfs.append(df)
            print(f"  {filename}: {len(df)} rows")
        else:
            print(f"  {filename}: NOT FOUND")

    if not dfs:
        print("No works files found")
        return

    combined = pd.concat(dfs, ignore_index=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)
    print(f"  -> {output_path}: {len(combined)} rows")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)

    print("\nConsolidating aggregate files:")
    consolidate_aggregate(data_dir, data_dir / "mplads_aggregate.csv")

    print("\nConsolidating works files:")
    consolidate_works(data_dir, data_dir / "mplads_works.csv")

    print("\nDone.")


if __name__ == "__main__":
    main()
