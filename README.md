# MPLADS Spending Analysis

Pipeline to analyze MP spending under MPLADS (Members of Parliament Local Area Development Scheme).

## Key Findings (18th Lok Sabha, 543 MPs)

| Stage | Amount | Rate |
|-------|--------|------|
| Allocated | ₹8,269 Cr | 100% |
| Recommended | ₹4,775 Cr | 58% of allocated |
| Sanctioned | ₹3,544 Cr | 43% of allocated |
| Completed | ₹1,051 Cr | 13% of allocated |

**Per-MP Statistics:**
- Median completion rate: **7.3%** (mean 12.6%)
- 18% of MPs have **zero completions** (96 MPs)
- Only 22 MPs (4%) have >50% completion rate
- 88,611 works recommended → 21,775 completed (25% conversion)

**Bottleneck:** Recommendation (only 58% of allocation recommended) and execution (only 32% of sanctioned works completed).

## Competitiveness Analysis

Does electoral competition drive MPLADS spending? We merged 2024 election results to test whether MPs in closer races complete more works.

| Seat Type | N | Mean Completion | Median Completion |
|-----------|---|-----------------|-------------------|
| Safe (>15% margin) | 191 | 12.0% | 7.3% |
| Competitive (5-15%) | 218 | 11.9% | 6.8% |
| Marginal (<5%) | 131 | 14.8% | 8.8% |

**Finding:** Weak relationship. Correlation between vote margin and completion is -0.03. Marginal seats show slightly higher completion, but the effect is small.

**Party-wise (top 5 by N):**
| Party | MPs | Mean Completion |
|-------|-----|-----------------|
| BJP | 237 | 12.0% |
| INC | 99 | 9.9% |
| SP | 38 | 17.2% |
| TMC | 29 | 10.0% |
| DMK | 22 | 19.3% |

## Scripts

```
src/
├── _client.py          # Shared HTTP client, throttling, caching
├── fetch_mplads.py     # Main scraper: gets MPs + spending tiles in one pass
├── fetch_works.py      # Fetch work-level details (optional)
├── fetch_elections.py  # Download election results (2019, 2024)
├── analyze.py          # Spending + competitiveness analysis
└── check_data.py       # Check data collection progress
```

## Data Files

```
data/
├── mplads_18ls.csv                  # 18th Lok Sabha spending data
├── mplads_17ls.csv                  # 17th Lok Sabha spending data (when available)
├── final/
│   └── mp_spending_with_elections.csv  # Merged with election competitiveness
└── raw/
    ├── elections_18ls.csv           # 2024 election results with margins
    ├── elections_17ls.csv           # 2019 election results with margins
    └── mplads_*_cache.jsonl         # Cache for resumability
```

## Quick Start

```bash
uv sync

# Fetch all MP spending data (resumable)
uv run python src/fetch_mplads.py --tenure-id 7  # 18th LS
uv run python src/fetch_mplads.py --tenure-id 5  # 17th LS

# Fetch election results
uv run python src/fetch_elections.py

# Analyze (includes competitiveness)
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
- **17th vs 18th LS:** The 18th Lok Sabha began in June 2024 with works still in progress. The 17th LS ran full tenure (2019-2024), hence higher completion rates.
