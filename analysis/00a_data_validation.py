#!/usr/bin/env python3
"""Data validation for MPLADS analysis - run FIRST before any analysis."""

import pandas as pd
from _data import DATA_DIR, get_cleaning_report, load_aggregate_data, load_works_data


def show_cleaning_tally() -> None:
    """Show data cleaning tally for all work-level datasets."""
    print("=" * 80)
    print("0. DATA CLEANING SUMMARY")
    print("=" * 80)

    for source, label in [("ls17", "17th LS"), ("ls18", "18th LS"), ("rs", "Rajya Sabha")]:
        archive_path = DATA_DIR / f"works_{source}.csv.tar.gz"
        if not archive_path.exists():
            print(f"\n{label}: Archive not found")
            continue

        _, stats = load_works_data(source, clean=True)
        print(f"\n{label}:")
        print("-" * 40)
        for line in get_cleaning_report(stats).split("\n")[2:]:
            print(f"  {line}")


def check_trimming_decision() -> None:
    """Check data quality by month to determine if trimming is needed."""
    print("\n" + "=" * 80)
    print("1. TRIMMING DECISION: Monthly Data Quality Check")
    print("=" * 80)

    ls17, _ = load_works_data("ls17", clean=False)

    ls17["rec_date"] = pd.to_datetime(
        ls17["RECOMMENDATION_DATE"], format="%d-%b-%Y", errors="coerce"
    )

    ls17["month"] = ls17["rec_date"].dt.to_period("M")
    monthly = (
        ls17[ls17["rec_date"].notna()]
        .groupby("month")
        .agg(
            {
                "ACTIVITY_NAME": "count",
                "IDA_NAME": lambda x: x.notna().mean() * 100,
                "RECOMMENDATION_DATE": lambda x: x.notna().mean() * 100,
            }
        )
    )
    monthly.columns = ["N Records", "IDA_NAME %", "REC_DATE %"]

    print("\nMonthly recommendation counts (17th LS):")
    print("-" * 60)

    focus_months = monthly[
        (monthly.index >= pd.Period("2023-04")) & (monthly.index <= pd.Period("2023-09"))
    ]
    print(focus_months.round(1).to_string())

    pre_july = monthly[
        (monthly.index >= pd.Period("2023-04")) & (monthly.index <= pd.Period("2023-06"))
    ]
    post_july = monthly[(monthly.index >= pd.Period("2023-07"))]

    print("\n\nCOMPARISON: Apr-Jun 2023 vs Jul+ 2023")
    print("-" * 60)
    print(f"Apr-Jun 2023: {pre_july['N Records'].sum():,} records, avg IDA coverage: {pre_july['IDA_NAME %'].mean():.1f}%")
    print(f"Jul+ 2023:    {post_july['N Records'].sum():,} records, avg IDA coverage: {post_july['IDA_NAME %'].mean():.1f}%")

    if pre_july["N Records"].sum() < post_july["N Records"].mean():
        print("\n--> RECOMMENDATION: Data appears sparse in Apr-Jun 2023.")
        print("    Consider TRIM_TO_JULY = True if focusing on complete data.")
    else:
        print("\n--> RECOMMENDATION: Apr-Jun 2023 data looks reasonable.")
        print("    TRIM_TO_JULY = False is appropriate.")


def cross_validate_aggregates() -> None:
    """Verify aggregate CSV totals match work-level sums."""
    print("\n" + "=" * 80)
    print("2. CROSS-VALIDATION: Aggregate vs Work-Level Data")
    print("=" * 80)

    aggregate = load_aggregate_data("all")
    agg_17ls = aggregate[aggregate["tenure_label"] == "17th Lok Sabha"]

    ls17_works, _ = load_works_data("ls17", clean=False)

    agg_total_rec = agg_17ls["recommended_cr"].sum()
    agg_total_comp = agg_17ls["completed_cr"].sum()
    agg_n_rec = agg_17ls["n_recommended"].sum()
    agg_n_comp = agg_17ls["n_completed"].sum()

    works_rec = ls17_works[ls17_works["RECOMMENDATION_DATE"].notna()]
    works_comp = ls17_works[ls17_works["ACTUAL_END_DATE"].notna()]

    works_rec_amount = works_rec["RECOMMENDED_AMOUNT"].sum() / 1e7
    works_comp_amount = works_comp["ACTUAL_AMOUNT"].sum() / 1e7

    works_n_rec = works_rec["ACTIVITY_NAME"].nunique()
    works_n_comp = works_comp["ACTIVITY_NAME"].nunique()

    print("\n17th Lok Sabha Comparison:")
    print("-" * 60)
    print(f"{'Metric':<25} {'Aggregate':<15} {'Work-Level':<15} {'Match?':<10}")
    print("-" * 60)

    rec_match = abs(agg_total_rec - works_rec_amount) / agg_total_rec < 0.05 if agg_total_rec > 0 else True
    comp_match = abs(agg_total_comp - works_comp_amount) / agg_total_comp < 0.05 if agg_total_comp > 0 else True
    n_rec_match = abs(agg_n_rec - works_n_rec) / agg_n_rec < 0.05 if agg_n_rec > 0 else True
    n_comp_match = abs(agg_n_comp - works_n_comp) / agg_n_comp < 0.05 if agg_n_comp > 0 else True

    print(f"{'Recommended (Cr)':<25} {agg_total_rec:>12,.1f}   {works_rec_amount:>12,.1f}   {'OK' if rec_match else 'MISMATCH'}")
    print(f"{'Completed (Cr)':<25} {agg_total_comp:>12,.1f}   {works_comp_amount:>12,.1f}   {'OK' if comp_match else 'MISMATCH'}")
    print(f"{'N Recommended':<25} {agg_n_rec:>12,.0f}   {works_n_rec:>12,}   {'OK' if n_rec_match else 'MISMATCH'}")
    print(f"{'N Completed':<25} {agg_n_comp:>12,.0f}   {works_n_comp:>12,}   {'OK' if n_comp_match else 'MISMATCH'}")

    if not all([rec_match, comp_match, n_rec_match, n_comp_match]):
        print("\nWARNING: Some metrics show >5% discrepancy.")
        print("This may be due to:")
        print("  - Aggregate data being a snapshot vs work-level being cumulative")
        print("  - Different calculation methods for totals")
        print("  - Data extraction timing differences")
    else:
        print("\nAll metrics within 5% tolerance.")


def check_duplicate_activities() -> None:
    """Check for duplicate ACTIVITY_NAMEs in work-level data."""
    print("\n" + "=" * 80)
    print("3. DUPLICATE CHECK: ACTIVITY_NAME Uniqueness")
    print("=" * 80)

    for source, label in [("ls17", "17th LS"), ("ls18", "18th LS"), ("rs", "Rajya Sabha")]:
        archive_path = DATA_DIR / f"works_{source}.csv.tar.gz"
        if not archive_path.exists():
            print(f"\n{label}: Archive not found")
            continue

        df, _ = load_works_data(source, clean=False)
        total_records = len(df)
        unique_activities = df["ACTIVITY_NAME"].nunique()
        dup_rate = (total_records - unique_activities) / total_records * 100

        print(f"\n{label}:")
        print(f"  Total records: {total_records:,}")
        print(f"  Unique ACTIVITY_NAMEs: {unique_activities:,}")
        print(f"  Duplicate rate: {dup_rate:.1f}%")

        if dup_rate > 0:
            rec_activities = df[df["RECOMMENDATION_DATE"].notna()]["ACTIVITY_NAME"].nunique()
            comp_activities = df[df["ACTUAL_END_DATE"].notna()]["ACTIVITY_NAME"].nunique()
            print(f"  Activities with recommendation: {rec_activities:,}")
            print(f"  Activities with completion: {comp_activities:,}")


def check_data_anomalies() -> None:
    """Flag any obvious data anomalies."""
    print("\n" + "=" * 80)
    print("4. ANOMALY CHECK: Data Quality Flags")
    print("=" * 80)

    ls17, _ = load_works_data("ls17", clean=False)

    print("\n4.1 Date Ranges:")
    ls17["rec_date"] = pd.to_datetime(ls17["RECOMMENDATION_DATE"], format="%d-%b-%Y", errors="coerce")
    ls17["comp_date"] = pd.to_datetime(ls17["ACTUAL_END_DATE"], format="%d-%b-%Y", errors="coerce")

    print(f"  Recommendation dates: {ls17['rec_date'].min()} to {ls17['rec_date'].max()}")
    print(f"  Completion dates: {ls17['comp_date'].min()} to {ls17['comp_date'].max()}")

    print("\n4.2 Amount Ranges:")
    rec_amounts = ls17[ls17["RECOMMENDED_AMOUNT"].notna()]["RECOMMENDED_AMOUNT"]
    print(f"  Recommended: Rs {rec_amounts.min():,.0f} to Rs {rec_amounts.max():,.0f}")
    print(f"  Median: Rs {rec_amounts.median():,.0f}")

    large_amounts = (rec_amounts > 1e8).sum()
    if large_amounts > 0:
        print(f"  WARNING: {large_amounts} recommendations > Rs 1 Cr")

    print("\n4.3 Missing Critical Fields:")
    print(f"  RECOMMENDATION_DATE missing: {ls17['RECOMMENDATION_DATE'].isna().sum():,} ({ls17['RECOMMENDATION_DATE'].isna().mean()*100:.1f}%)")
    print(f"  ACTUAL_END_DATE missing: {ls17['ACTUAL_END_DATE'].isna().sum():,} ({ls17['ACTUAL_END_DATE'].isna().mean()*100:.1f}%)")
    print(f"  ACTIVITY_NAME missing: {ls17['ACTIVITY_NAME'].isna().sum():,} ({ls17['ACTIVITY_NAME'].isna().mean()*100:.1f}%)")

    print("\n4.4 State Coverage:")
    state_counts = ls17.groupby("state_name")["ACTIVITY_NAME"].count()
    print(f"  States with data: {len(state_counts)}")
    print(f"  Min records per state: {state_counts.min():,} ({state_counts.idxmin()})")
    print(f"  Max records per state: {state_counts.max():,} ({state_counts.idxmax()})")


def main() -> None:
    print("MPLADS DATA VALIDATION REPORT")
    print("=" * 80)
    print("Run this script BEFORE any analysis to check data quality.\n")

    show_cleaning_tally()
    check_trimming_decision()
    cross_validate_aggregates()
    check_duplicate_activities()
    check_data_anomalies()

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Review any WARNINGs above")
    print("  2. Run: uv run python analysis/00_descriptive_stats.py")
    print("  3. Run: uv run jupyter nbconvert --execute analysis/02_electoral_targeting.ipynb")
    print("  4. Run: uv run jupyter nbconvert --execute analysis/03_project_analysis.ipynb")


if __name__ == "__main__":
    main()
