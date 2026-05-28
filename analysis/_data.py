"""Centralized data loading and cleaning for MPLADS analysis."""

import tarfile
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"

_CACHE: dict[str, pd.DataFrame] = {}

WORK_ARCHIVES = {
    "ls17": "works_ls17.csv.tar.gz",
    "ls18": "works_ls18.csv.tar.gz",
    "rs": "works_rs.csv.tar.gz",
}


def _load_archive(archive_path: Path) -> pd.DataFrame:
    """Load CSV from compressed archive."""
    with tarfile.open(archive_path, "r:gz") as tar:
        csv_member = [
            m
            for m in tar.getmembers()
            if m.name.endswith(".csv") and not m.name.startswith("._")
        ][0]
        return pd.read_csv(
            tar.extractfile(csv_member), low_memory=False, on_bad_lines="skip"
        )


def clean_works(
    df: pd.DataFrame,
    drop_future_dates: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Clean work-level data.

    Cleaning rules:
    - Drop records with missing ACTIVITY_NAME
    - Drop records with zero RECOMMENDED_AMOUNT
    - Drop records with invalid dates (before 2019-05-01 or after 2030)
    - Flag (optionally drop) future completion dates

    Args:
        df: Raw works DataFrame
        drop_future_dates: If True, drop records with completion dates in the future

    Returns:
        cleaned_df: DataFrame with bad records removed
        drop_stats: Dictionary with drop counts and reasons
    """
    original_count = len(df)
    stats = {
        "original_count": original_count,
        "missing_activity_name": 0,
        "zero_recommended_amount": 0,
        "invalid_rec_dates": 0,
        "future_completion_dates": 0,
        "dropped_future_dates": 0,
        "total_dropped": 0,
        "retained_count": 0,
    }

    df = df.copy()

    # Parse dates once
    df["_rec_date"] = pd.to_datetime(
        df["RECOMMENDATION_DATE"], format="%d-%b-%Y", errors="coerce"
    )
    df["_comp_date"] = pd.to_datetime(
        df["ACTUAL_END_DATE"], format="%d-%b-%Y", errors="coerce"
    )

    # Define date boundaries
    min_valid_date = pd.Timestamp("2019-05-01")  # LS17 started late May 2019
    max_valid_date = pd.Timestamp("2030-01-01")
    today = pd.Timestamp(datetime.now().date())

    # Drop missing ACTIVITY_NAME
    missing_activity = df["ACTIVITY_NAME"].isna()
    stats["missing_activity_name"] = missing_activity.sum()
    df = df[~missing_activity]

    # Drop zero recommended amounts
    zero_amount = (df["RECOMMENDED_AMOUNT"] == 0) | df["RECOMMENDED_AMOUNT"].isna()
    stats["zero_recommended_amount"] = zero_amount.sum()
    df = df[~zero_amount]

    # Drop invalid recommendation dates (out of range)
    # Only check records that have a recommendation date
    has_rec_date = df["_rec_date"].notna()
    invalid_rec_dates = has_rec_date & (
        (df["_rec_date"] < min_valid_date) | (df["_rec_date"] > max_valid_date)
    )
    stats["invalid_rec_dates"] = invalid_rec_dates.sum()
    df = df[~invalid_rec_dates]

    # Flag/drop future completion dates
    has_comp_date = df["_comp_date"].notna()
    future_dates = has_comp_date & (df["_comp_date"] > today)
    stats["future_completion_dates"] = future_dates.sum()

    if drop_future_dates:
        stats["dropped_future_dates"] = future_dates.sum()
        df = df[~future_dates]

    # Clean up temporary columns
    df = df.drop(columns=["_rec_date", "_comp_date"])

    stats["retained_count"] = len(df)
    stats["total_dropped"] = original_count - len(df)

    return df, stats


def load_works_data(
    source: Literal["ls17", "ls18", "rs"] | str = "ls17",
    clean: bool = True,
    drop_future_dates: bool = False,
    use_cache: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """Load work-level data with optional cleaning.

    Args:
        source: One of "ls17", "ls18", "rs", or a full archive filename
        clean: If True, apply cleaning rules
        drop_future_dates: If True and clean=True, drop future completion dates
        use_cache: If True, cache raw data in memory

    Returns:
        df: DataFrame (cleaned if clean=True)
        stats: Dict with drop counts and reasons (empty if clean=False)
    """
    # Resolve source to filename
    if source in WORK_ARCHIVES:
        archive_name = WORK_ARCHIVES[source]
    else:
        archive_name = source

    archive_path = DATA_DIR / archive_name
    cache_key = str(archive_path)

    # Load from cache or file
    if use_cache and cache_key in _CACHE:
        df = _CACHE[cache_key].copy()
    else:
        df = _load_archive(archive_path)
        if use_cache:
            _CACHE[cache_key] = df.copy()

    # Apply cleaning if requested
    if clean:
        return clean_works(df, drop_future_dates=drop_future_dates)
    else:
        return df, {}


def load_aggregate_data(
    source: Literal["ls17", "ls18", "rs", "all"] = "all",
) -> pd.DataFrame:
    """Load aggregate data.

    Args:
        source: One of "ls17", "ls18", "rs", or "all"

    Returns:
        DataFrame with aggregate MPLADS data
    """
    df = pd.read_csv(DATA_DIR / "mplads_aggregate.csv")

    if source == "all":
        return df
    elif source == "ls17":
        return df[df["tenure_label"] == "17th Lok Sabha"].copy()
    elif source == "ls18":
        return df[df["tenure_label"] == "18th Lok Sabha"].copy()
    elif source == "rs":
        return df[df["tenure_label"] == "Rajya Sabha"].copy()
    else:
        raise ValueError(f"Unknown source: {source}")


def get_cleaning_report(stats: dict) -> str:
    """Format cleaning statistics as a readable report."""
    if not stats:
        return "No cleaning applied."

    lines = [
        "Data Cleaning Report",
        "=" * 40,
        f"Original records:      {stats['original_count']:>10,}",
        f"Missing ACTIVITY_NAME: {stats['missing_activity_name']:>10,}",
        f"Zero RECOMMENDED_AMT:  {stats['zero_recommended_amount']:>10,}",
        f"Invalid rec dates:     {stats['invalid_rec_dates']:>10,}",
        f"Future comp dates:     {stats['future_completion_dates']:>10,} (flagged)",
    ]

    if stats.get("dropped_future_dates", 0) > 0:
        lines.append(
            f"  -> Dropped future:   {stats['dropped_future_dates']:>10,}"
        )

    lines.extend(
        [
            "-" * 40,
            f"Total dropped:         {stats['total_dropped']:>10,}",
            f"Retained records:      {stats['retained_count']:>10,}",
            f"Retention rate:        {stats['retained_count']/stats['original_count']*100:>9.1f}%",
        ]
    )

    return "\n".join(lines)


def clear_cache() -> None:
    """Clear the data cache."""
    _CACHE.clear()
