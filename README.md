# MPLADS Spending Analysis

Pipeline to analyze MP spending under MPLADS (Members of Parliament Local Area Development Scheme).

## Data Coverage

| Body | Tenure | MPs | Status |
|------|--------|-----|--------|
| Lok Sabha | 18th (2024-present) | 543 | Complete |
| Lok Sabha | 17th (2019-2024) | 557 | Complete |
| Rajya Sabha | All current | 219 | Complete |

Note: Rajya Sabha data is not tenure-separated in the portal API. All current RS MPs are fetched together, with individual tenure info (e.g., "2020-26") embedded in MP names.

## Analysis 1: Tenure-Level Summary

**Estimand:** Total allocation utilization rate per tenure.

**Methodology:** Sum all MP-level amounts within each tenure and compute aggregate rates.

**Unit of Analysis:** Parliamentary tenure (Lok Sabha term or Rajya Sabha term).

**Results:**

| Tenure | MPs | Allocated | Completed | Completion Rate |
|--------|-----|-----------|-----------|-----------------|
| 18th LS (current) | 553 | Rs 8,248 Cr | Rs 1,044 Cr | **12.7%** |
| 17th LS (2019-24) | 557 | Rs 4,768 Cr | Rs 2,358 Cr | **49.5%** |
| Rajya Sabha | 219 | Rs 3,619 Cr | Rs 694 Cr | **19.2%** |

**Key Finding:** The 17th LS shows much higher completion rates because MPs had a full 5-year term. The 18th LS began in June 2024 and works are still in progress.

## Analysis 2: MP-Level Completion Distribution

**Estimand:** Distribution of individual MP completion rates.

**Methodology:** For each MP, compute `completion_rate = completed_amount / allocated_amount`, then examine the distribution across all MPs.

**Unit of Analysis:** Individual MP.

**Results (18th Lok Sabha):**

| Percentile | Completion Rate |
|------------|-----------------|
| 0th (min) | 0.0% |
| 10th | 0.0% |
| 25th | 3.4% |
| 50th (median) | 7.3% |
| 75th | 17.8% |
| 90th | 34.9% |
| 100th (max) | 66.0% |

**Completion Buckets:**
- Zero completion: 96 MPs (18%)
- 0-10%: 253 MPs
- 10-25%: 106 MPs
- 25-50%: 72 MPs
- >50%: 16 MPs (3%)

## Analysis 3: Competitiveness Analysis (Lok Sabha only)

**Estimand:** Correlation between electoral competitiveness and MPLADS spending completion.

**Hypothesis:** MPs in marginal seats may complete more works to strengthen electoral position.

**Methodology:**
1. Merge election results (vote margin = winner% - runner-up%) with MPLADS data
2. Categorize seats: marginal (<5% margin), competitive (5-15%), safe (>15%)
3. Compare mean/median completion rates across categories
4. Compute Pearson correlation between margin and completion rate

**Unit of Analysis:** Lok Sabha MP-constituency pair.

**Results (18th Lok Sabha):**

| Seat Type | N | Mean Completion | Median Completion |
|-----------|---|-----------------|-------------------|
| Safe (>15% margin) | 191 | 12.0% | 7.3% |
| Competitive (5-15%) | 218 | 11.9% | 6.8% |
| Marginal (<5%) | 131 | 14.8% | 8.8% |

**Correlation (margin vs completion):** r = -0.03

**Conclusion:** Weak relationship. Marginal seats show slightly higher completion (+2-3 percentage points), but the effect is small and statistically weak.

## Analysis 4: Party-wise Completion (Lok Sabha only)

**Estimand:** Mean completion rate by political party.

**Methodology:** Group MPs by winning party, compute mean/median completion rates.

**Unit of Analysis:** Political party within tenure.

**Results (18th Lok Sabha, top parties by N):**

| Party | MPs | Mean Completion | Median Completion |
|-------|-----|-----------------|-------------------|
| BJP | 237 | 12.0% | 7.3% |
| INC | 99 | 9.9% | 6.8% |
| SP | 38 | 17.2% | 11.2% |
| TMC | 29 | 10.0% | 6.4% |
| DMK | 22 | 19.3% | 15.5% |

## Data Files

```
data/
├── mplads_18ls.csv          # 18th Lok Sabha aggregate spending
├── mplads_17ls.csv          # 17th Lok Sabha aggregate spending
├── mplads_rs.csv            # Rajya Sabha aggregate spending (all current MPs)
├── mplads_aggregate.csv     # Combined aggregate data (all bodies)
├── mplads_works.csv         # Work-level detail data (all bodies)
├── works_ls18.csv           # Work details for 18th LS
├── works_ls17.csv           # Work details for 17th LS
├── works_rs.csv             # Work details for RS
├── elections/
│   ├── elections_18ls.csv   # 2024 election results with margins
│   └── elections_17ls.csv   # 2019 election results with margins
└── raw/
    └── *_cache.jsonl        # API response caches for resumability
```

## Scripts

```
src/
├── _client.py          # Shared HTTP client, throttling, caching
├── fetch_mplads.py     # Scrape Lok Sabha aggregate spending data
├── fetch_mplads_rs.py  # Scrape Rajya Sabha aggregate spending data
├── fetch_works.py      # Scrape work-level details
├── fetch_elections.py  # Download election results
├── consolidate.py      # Combine source files into aggregate outputs
├── analyze.py          # Analysis and reporting
└── check_data.py       # Check data collection progress
```

## Quick Start

```bash
uv sync

# Fetch Lok Sabha aggregate spending data
uv run python src/fetch_mplads.py --tenure-id 7 --house 2 --out data/mplads_18ls.csv   # 18th LS
uv run python src/fetch_mplads.py --tenure-id 5 --house 2 --out data/mplads_17ls.csv   # 17th LS

# Fetch Rajya Sabha aggregate spending data (separate script, no tenure separation)
uv run python src/fetch_mplads_rs.py --out data/mplads_rs.csv

# Fetch election results
uv run python src/fetch_elections.py

# Consolidate into single files
uv run python src/consolidate.py

# Analyze
uv run python src/analyze.py
uv run python src/analyze.py --aggregate mplads_aggregate.csv  # Use consolidated file
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
- `getStateData`, `getConstituencyData` - State/constituency lookups
- `getMpAndConstCombo` - MPs by constituency (Lok Sabha)
- `getMpNamesData` - MPs by state (Rajya Sabha)

**Lok Sabha API format:**
- MPs: `getMpAndConstCombo` with `const_combo = "constituency_id,2,tenure_id"`
- Tiles: `getTilesData` with `uname = "state_id,const_id,mp_id,2,tenure_id"`

**Rajya Sabha API format:**
- MPs: `getMpNamesData` with `state_combo = "state_id,1"`
- Tiles: `getTilesData` with `uname = "state_id,0,mp_id,1"` (no tenure parameter)

Requires session cookies from `/digigov/dashboard.html`.

## Notes

- **Resumability:** JSONL cache. Re-running skips cached data.
- **Rate Limiting:** Server rate-limits aggressively. Scripts retry with exponential backoff.
- **Data Model:** Primary key is (mp_id, tenure_id, house). Same MP across tenures = separate rows.
- **17th vs 18th LS:** The 18th Lok Sabha began in June 2024 with works still in progress. The 17th LS ran full tenure (2019-2024), hence higher completion rates.
