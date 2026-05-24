#!/usr/bin/env python3
"""Fetch election results for 17th and 18th Lok Sabha.

Sources:
- 2024 (18th LS): https://github.com/thecont1/india-votes-data
- 2019 (17th LS): https://github.com/pratapvardhan/Elections-India-2019

Computes vote margins and competitiveness classification.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import requests

URLS = {
    "18ls": "https://raw.githubusercontent.com/thecont1/india-votes-data/main/archive/2024%20Parliamentary%20Elections%20India.csv",
    "17ls": "https://raw.githubusercontent.com/pratapvardhan/Elections-India-2019/master/eci-2019.csv",
}


def fetch_csv(url: str, sep: str = ",") -> pd.DataFrame:
    """Fetch CSV from URL."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    from io import StringIO

    return pd.read_csv(StringIO(resp.text), sep=sep)


def process_2024(df: pd.DataFrame) -> pd.DataFrame:
    """Process 2024 election data.

    Columns: State, Constituency, Party, Candidate, Votes, State ID, Constituency ID
    """
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(
        columns={
            "State": "state",
            "Constituency": "constituency",
            "Party": "party",
            "Candidate": "candidate",
            "Votes": "votes",
        }
    )
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    return compute_margins(df, "18th Lok Sabha")


def process_2019(df: pd.DataFrame) -> pd.DataFrame:
    """Process 2019 election data.

    Columns: OSN, Candidate, Party, EVM Votes, Postal Votes, Total Votes, %, State, Constituency, ...
    """
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(
        columns={
            "State": "state",
            "Constituency": "constituency",
            "Party": "party",
            "Candidate": "candidate",
            "Total Votes": "votes",
        }
    )
    df["votes"] = (
        df["votes"]
        .astype(str)
        .str.replace(",", "")
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
    )
    return compute_margins(df, "17th Lok Sabha")


def compute_margins(df: pd.DataFrame, tenure: str) -> pd.DataFrame:
    """Compute vote margins for each constituency."""
    results = []

    for (state, const), group in df.groupby(["state", "constituency"]):
        group = group.sort_values("votes", ascending=False)
        if len(group) < 2:
            continue

        total_votes = group["votes"].sum()
        if total_votes == 0:
            continue

        winner = group.iloc[0]
        runner_up = group.iloc[1]

        margin_votes = winner["votes"] - runner_up["votes"]
        margin_pct = 100 * margin_votes / total_votes

        if margin_pct > 15:
            competitiveness = "safe"
        elif margin_pct > 5:
            competitiveness = "competitive"
        else:
            competitiveness = "marginal"

        results.append(
            {
                "tenure": tenure,
                "state": state,
                "constituency": const,
                "winner": winner["candidate"],
                "winner_party": winner["party"],
                "winner_votes": winner["votes"],
                "runner_up": runner_up["candidate"],
                "runner_up_party": runner_up["party"],
                "runner_up_votes": runner_up["votes"],
                "total_votes": total_votes,
                "margin_votes": margin_votes,
                "margin_pct": round(margin_pct, 2),
                "competitiveness": competitiveness,
            }
        )

    return pd.DataFrame(results)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="data/elections")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching 2024 (18th LS) election data...")
    df_2024 = fetch_csv(URLS["18ls"], sep=";")
    print(f"  Raw rows: {len(df_2024)}")
    elections_18 = process_2024(df_2024)
    out_18 = out_dir / "elections_18ls.csv"
    elections_18.to_csv(out_18, index=False)
    print(f"  Constituencies: {len(elections_18)}")
    print(f"  Saved to {out_18}")

    print("\nFetching 2019 (17th LS) election data...")
    df_2019 = fetch_csv(URLS["17ls"])
    print(f"  Raw rows: {len(df_2019)}")
    elections_17 = process_2019(df_2019)
    out_17 = out_dir / "elections_17ls.csv"
    elections_17.to_csv(out_17, index=False)
    print(f"  Constituencies: {len(elections_17)}")
    print(f"  Saved to {out_17}")

    print("\nCompetitiveness breakdown:")
    for tenure, df in [("18th LS", elections_18), ("17th LS", elections_17)]:
        print(f"\n{tenure}:")
        counts = df["competitiveness"].value_counts()
        for cat in ["safe", "competitive", "marginal"]:
            n = counts.get(cat, 0)
            pct = 100 * n / len(df)
            print(f"  {cat:12}: {n:3} ({pct:.0f}%)")


if __name__ == "__main__":
    main()
