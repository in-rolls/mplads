"""
Merge MPLADS works data (18th Lok Sabha) with 2019 election results.

Since 18th LS election data is not available, we use 2019 (17th LS) results
as a proxy for constituency competitiveness characteristics.

This is a data prep step. Run before 02_electoral_targeting.ipynb.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
ELECTION_DATA_PATH = DATA_DIR / "elections" / "gen_election_data.csv"


def clean_constituency_name(name: str) -> str:
    """Standardize constituency names for matching."""
    if pd.isna(name):
        return ""
    name = str(name).upper().strip()
    name = re.sub(r"\(S[TC]\)$", "", name).strip()
    name = re.sub(r"\s+", " ", name)
    name = name.replace("_", " ").replace("-", " ")
    name = name.replace("&", "AND")
    return name


def load_mplads_data() -> pd.DataFrame:
    """Load and aggregate MPLADS works data by MP/constituency."""
    df = pd.read_csv(DATA_DIR / "works_ls18.csv", low_memory=False)

    df["RECOMMENDED_AMOUNT"] = pd.to_numeric(df["RECOMMENDED_AMOUNT"], errors="coerce")
    df["ACTUAL_AMOUNT"] = pd.to_numeric(df["ACTUAL_AMOUNT"], errors="coerce")

    df = df[df["tile_label"].notna() & (df["tile_label"] != "")]

    agg = df.groupby(["state_name", "constituency_name", "mp_id", "mp_name"]).agg(
        total_works=("WORK_ID", "count"),
        works_recommended=("tile_label", lambda x: (x == "Works Recommended").sum()),
        works_sanctioned=("tile_label", lambda x: (x == "Works Sanctioned").sum()),
        works_completed=("tile_label", lambda x: (x == "Works Completed").sum()),
        total_recommended_amount=("RECOMMENDED_AMOUNT", "sum"),
        total_actual_amount=("ACTUAL_AMOUNT", "sum"),
        unique_categories=("WORK_CATEGORY", "nunique"),
        categories_list=("WORK_CATEGORY", lambda x: "|".join(x.dropna().unique())),
    ).reset_index()

    agg["completion_rate"] = agg["works_completed"] / agg["works_sanctioned"].replace(0, np.nan)
    agg["sanction_rate"] = agg["works_sanctioned"] / agg["works_recommended"].replace(0, np.nan)

    agg["constituency_clean"] = agg["constituency_name"].apply(clean_constituency_name)

    return agg


def load_election_data() -> pd.DataFrame:
    """Load 2019 election data for winners only."""
    df = pd.read_csv(ELECTION_DATA_PATH, low_memory=False)

    df = df[(df["Year"] == 2019) & (df["Position"] == 1)]

    cols = [
        "State_Name", "Constituency_Name", "Constituency_Type",
        "Candidate", "Sex", "Party", "Votes", "Valid_Votes", "Electors",
        "Turnout_Percentage", "Vote_Share_Percentage", "Margin", "Margin_Percentage",
        "ENOP", "Party_Type_TCPD", "No_Terms", "Incumbent", "Recontest",
        "MyNeta_education", "TCPD_Prof_Main"
    ]
    df = df[cols].copy()

    df["constituency_clean"] = df["Constituency_Name"].apply(clean_constituency_name)
    df["state_clean"] = df["State_Name"].str.replace("_", " ").str.upper().str.strip()

    df["margin_category"] = pd.cut(
        df["Margin_Percentage"],
        bins=[-np.inf, 5, 10, 20, np.inf],
        labels=["Very Close (<5%)", "Close (5-10%)", "Safe (10-20%)", "Very Safe (>20%)"]
    )

    df["party_category"] = df["Party_Type_TCPD"].map({
        "National Party": "National",
        "State-based Party": "Regional",
        "State-based Party (Other State)": "Regional",
        "Independents": "Independent",
        "Local Party": "Regional"
    }).fillna("Other")

    nda_parties = ["BJP", "JDU", "LJSP", "SAD", "SS", "AIADMK", "TDP", "NPP", "NPF", "SKM", "AJSUP", "RLTP", "NDPP"]
    upa_parties = ["INC", "NCP", "DMK", "JKNC", "RJD", "IUML", "RSP", "KC(M)", "JMM", "MDMK", "VCK"]

    def get_alliance(party):
        if party in nda_parties:
            return "NDA"
        elif party in upa_parties:
            return "UPA"
        else:
            return "Other"

    df["alliance_2019"] = df["Party"].apply(get_alliance)

    return df


def merge_datasets(mplads: pd.DataFrame, election: pd.DataFrame) -> pd.DataFrame:
    """Merge MPLADS and election data on constituency."""
    merged = mplads.merge(
        election,
        on="constituency_clean",
        how="left",
        suffixes=("_mplads", "_election")
    )

    return merged


def generate_match_report(mplads: pd.DataFrame, merged: pd.DataFrame) -> dict:
    """Generate a report on matching quality."""
    total_mps = len(mplads)
    matched_mps = merged["Constituency_Name"].notna().sum()
    unmatched = mplads[~mplads["constituency_clean"].isin(
        merged[merged["Constituency_Name"].notna()]["constituency_clean"]
    )]

    return {
        "total_mps": total_mps,
        "matched_mps": matched_mps,
        "match_rate": matched_mps / total_mps * 100,
        "unmatched_constituencies": unmatched["constituency_name"].unique().tolist()[:20]
    }


def main():
    print("Loading MPLADS data...")
    mplads = load_mplads_data()
    print(f"  Loaded {len(mplads)} MP records")

    print("\nLoading election data...")
    election = load_election_data()
    print(f"  Loaded {len(election)} constituency records from 2019")

    print("\nMerging datasets...")
    merged = merge_datasets(mplads, election)

    report = generate_match_report(mplads, merged)
    print(f"\nMatching Report:")
    print(f"  Total MPs: {report['total_mps']}")
    print(f"  Matched MPs: {report['matched_mps']}")
    print(f"  Match Rate: {report['match_rate']:.1f}%")

    if report["unmatched_constituencies"]:
        print(f"\n  Sample unmatched constituencies:")
        for c in report["unmatched_constituencies"][:10]:
            print(f"    - {c}")

    output_path = DATA_DIR / "mplads_election_merged.csv"
    merged.to_csv(output_path, index=False)
    print(f"\nSaved merged data to {output_path}")

    return merged


if __name__ == "__main__":
    main()
