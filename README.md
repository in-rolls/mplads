# MPLADS Spending Analysis

Pipeline to analyze MP spending under MPLADS (Members of Parliament Local Area Development Scheme).

## Key Findings (18th Lok Sabha, 398 MPs)

| Stage | Amount | Rate |
|-------|--------|------|
| Allocated | ₹6,038 Cr | 100% |
| Recommended | ₹3,424 Cr | 57% of allocated |
| Sanctioned | ₹2,482 Cr | 72% of recommended |
| Completed | ₹714 Cr | 25% of sanctioned |
| **Utilization** | | **11.8%** |

**Per-MP Statistics:**
- Median completion rate: **6.8%** (mean 11.8% - skewed by top performers)
- 17% of MPs have **zero completions** (67 MPs)
- Only 15 MPs (4%) have >50% completion rate
- 62,125 works recommended → 14,550 completed (23% conversion)

**Bottleneck:** Recommendation (only 57% of allocation recommended) and execution (only 25% of sanctioned works completed).

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
