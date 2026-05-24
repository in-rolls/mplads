# MPLADS Spending Analysis

Pipeline to analyze MP spending under MPLADS (Members of Parliament Local Area Development Scheme).

## Key Findings (Partial: 30 MPs, 3 States, 18th Lok Sabha)

| Metric | Value |
|--------|-------|
| Total Allocated | ₹433 Cr |
| Total Recommended | ₹218 Cr (50%) |
| Total Sanctioned | ₹195 Cr (89% of recommended) |
| Total Completed | ₹39 Cr (20% of sanctioned) |
| **Overall Utilization** | **9%** |

**The Bottleneck:** Sanction→Completion is the weakest link. 89% of recommendations get sanctioned, but only 20% of sanctioned works are completed.

## Scripts

```
src/
├── _client.py        # Shared HTTP client, throttling, caching
├── fetch_mplads.py   # Main scraper: gets MPs + spending tiles in one pass
├── fetch_works.py    # Fetch work-level details (optional)
├── analyze.py        # Spending analysis (pooled & per-MP metrics)
└── check_data.py     # Check data collection progress
```

## Data Files

```
data/
├── mplads_full.csv                  # Main output: one row per MP × tenure
├── final/
│   └── mp_spending_by_tenure.csv    # With computed metrics
└── raw/
    ├── mplads_full_cache.jsonl      # Cache for resumability
    └── unified_scraper.log          # Fetch log
```

## Quick Start

```bash
uv sync

# Fetch all MP spending data (resumable)
uv run python src/fetch_mplads.py --tenure-id 7  # 18th LS
uv run python src/fetch_mplads.py --tenure-id 5  # 17th LS

# Analyze (works with partial data)
uv run python src/analyze.py

# Check progress
uv run python src/check_data.py
```

## The Spending Funnel

Each MP gets Rs 5 Cr/year. The pipeline tracks:

```
Entitlement → Recommendation → Sanction → Completion
   (Rs 5 Cr)    (MP submits)    (DA approves)  (IA marks done)
```

Key metrics per MP:
- `recommendation_pct` = recommended / allocated
- `sanction_yield` = sanctioned / recommended
- `completion_pct` = completed / allocated

## What is MPLADS?

Each sitting MP gets Rs 5 crore annually for developmental works. Lok Sabha MPs recommend within their constituency; Rajya Sabha MPs within their state.

The eSAKSHI portal (live since April 2023) tracks the workflow. Only FY 2023-24 onward is on the portal.

## API

POST endpoints at `mplads.mospi.gov.in/rest/PreLoginDashboardData/`:
- `getTilesData` - Six dashboard tiles per MP
- `getTilesReportData` - Work-level details
- `getStateData`, `getConstituencyData`, `getMpAndConstCombo` - Lookups

Requires session cookies from `/digigov/dashboard.html`.

## Notes

- **Resumability:** JSONL cache. Re-running skips cached data.
- **Rate Limiting:** Server rate-limits aggressively. Scripts retry with exponential backoff.
- **Data Model:** Primary key is (mp_id, tenure_id). Same MP across tenures = separate rows.
