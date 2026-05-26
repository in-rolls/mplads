# MPLADS Data Collection & Analysis

Scrapes MP Local Area Development Scheme (MPLADS) spending data from the [eSAKSHI portal](https://mplads.mospi.gov.in) and analyzes spending patterns, including electoral competitiveness effects.

## TL;DR: The Spending Funnel

Of every Rs 100 allocated to MPs:

| Stage | Amount | What happens |
|-------|--------|--------------|
| Allocated | Rs 100 | MP's annual entitlement |
| Recommended | Rs 69 | MP proposes projects |
| Sanctioned | Rs 58 | District Authority approves |
| Completed | Rs 25 | Work marked finished |
| Expenditure | Rs 44 | Actual money released (includes ongoing works) |

**75% of allocated funds never reach completion.** Of every Rs 100, Rs 31 is lost at recommendation, Rs 11 at sanction, and Rs 33 between sanction and completion. Expenditure > Completed because expenditure includes payments for works still in progress.

*"From the perspective of a profit- and vote-maximizing politician, it is not clear why allocated money would remain unspent."*

## TL;DR: The Political Angle

**What explains variation? Almost nothing except tenure maturity.**

| Factor | Effect | Notes |
|--------|--------|-------|
| Tenure maturity | Huge | 17th LS (full term): 49% completion. 18th LS (new): 13% |
| Electoral competitiveness | Near zero | r = -0.02. Marginal vs safe seats: no meaningful difference |
| Party | Small, noisy | Some variation but high within-party variance dominates |

**Competitiveness (18th LS):**

| Seat Type | N | Rec % | Exp % | Comp % |
|-----------|---|-------|-------|--------|
| Safe (>15% margin) | 191 | 56% | 26% | 12% |
| Competitive (5-15%) | 218 | 57% | 25% | 12% |
| Marginal (<5%) | 131 | 61% | 30% | 15% |

Correlation (margin vs completion): **r = -0.02** → essentially zero. The pattern holds across all funnel stages.

**Party (18th LS, top parties):**

| Party | N | Rec % | Exp % | Comp % |
|-------|---|-------|-------|--------|
| BJP | 237 | 55% | 25% | 12% |
| INC | 99 | 61% | 25% | 10% |
| SP | 38 | 64% | 37% | 17% |
| TMC | 29 | 64% | 32% | 11% |
| DMK | 22 | 65% | 35% | 20% |

Within-party std dev = 30%, so party label explains little. The electoral incentive story doesn't hold: MPs in marginal seats don't spend more to shore up support. Most variation is idiosyncratic or tenure-driven.

---

## The Spending Funnel

Each MP receives Rs 5 crore annually under MPLADS. Funds flow through a multi-stage process:

```
Entitlement → Recommendation → Sanction → Completion
   (5 Cr/yr)     (MP proposes)    (DA approves)   (Work done)
```

**Key metrics:**
- `recommendation_pct`: % of allocated funds recommended by MP
- `sanction_yield`: % of recommended funds sanctioned by District Authority
- `completion_pct`: % of allocated funds for completed works

## Data Coverage

| Body | Tenure | MPs | Work Records |
|------|--------|-----|--------------|
| Lok Sabha 18th | 2024-present | 554 | 184K (compressed) |
| Lok Sabha 17th | 2019-2024 | 557 | 263K (compressed) |
| Rajya Sabha | Current | 219 | 62K (compressed) |

Note: Rajya Sabha data is not tenure-separated in the portal API. All current RS MPs are fetched together, with individual tenure info (e.g., "2020-26") embedded in MP names.

## Project Structure

```
mplads/
├── src/                    # Scraping scripts
│   ├── _client.py          # Shared HTTP client, caching, throttling
│   ├── fetch_mplads.py     # Lok Sabha aggregate spending
│   ├── fetch_mplads_rs.py  # Rajya Sabha aggregate spending
│   ├── fetch_works.py      # Work-level details (LS)
│   ├── fetch_works_rs.py   # Work-level details (RS)
│   ├── fetch_elections.py  # Election results (margins, competitiveness)
│   ├── consolidate.py      # Combine tenure files
│   ├── check_data.py       # Check data collection progress
│   └── export_cache.py     # Export cache to CSV
├── analysis/               # Analysis scripts (run in order: 00 → 01 → 02)
│   ├── _config.py          # Shared constants (colors, labels)
│   ├── 00_descriptive_stats.py   # Descriptive stats & visualizations
│   ├── 01_merge_election_mplads.py   # Merge MPLADS with election data
│   └── 02_electoral_targeting.ipynb  # Electoral targeting regression analysis
└── data/                   # Output files
    ├── mplads_18ls.csv
    ├── mplads_17ls.csv
    ├── mplads_rs.csv
    ├── mplads_aggregate.csv
    ├── works_ls18.csv.tar.gz
    ├── works_ls17.csv.tar.gz
    ├── works_rs.csv.tar.gz
    ├── elections/
    ├── final/
    └── raw/                # JSONL caches
```

## Quick Start

```bash
uv sync

# Fetch Lok Sabha aggregate spending data
uv run python src/fetch_mplads.py --tenure-id 7 --house 2 --out data/mplads_18ls.csv   # 18th LS
uv run python src/fetch_mplads.py --tenure-id 5 --house 2 --out data/mplads_17ls.csv   # 17th LS

# Fetch Rajya Sabha aggregate spending data
uv run python src/fetch_mplads_rs.py --out data/mplads_rs.csv

# Fetch work-level details
uv run python src/fetch_works.py --input data/mplads_18ls.csv --out data/works_ls18.csv
uv run python src/fetch_works.py --input data/mplads_17ls.csv --out data/works_ls17.csv
uv run python src/fetch_works_rs.py --input data/mplads_rs.csv --out data/works_rs.csv

# Fetch election results
uv run python src/fetch_elections.py

# Consolidate into single files
uv run python src/consolidate.py

# Analysis pipeline (run in order)
uv run python analysis/00_descriptive_stats.py      # Descriptive stats
uv run python analysis/01_merge_election_mplads.py  # Merge with election data
uv run jupyter execute analysis/02_electoral_targeting.ipynb  # Regression analysis
```

## Data Files

### Aggregate CSVs
- `mplads_18ls.csv` - 18th Lok Sabha MP spending (554 MPs)
- `mplads_17ls.csv` - 17th Lok Sabha MP spending (557 MPs)
- `mplads_rs.csv` - Rajya Sabha MP spending (219 MPs)
- `mplads_aggregate.csv` - Combined file

**Columns:** `tenure_label`, `house`, `state_id`, `state_name`, `constituency_id`, `constituency_name`, `mp_id`, `mp_name`, `allocated_cr`, `recommended_cr`, `sanctioned_cr`, `completed_cr`, `expenditure_cr`, `n_recommended`, `n_sanctioned`, `n_completed`

### Work-level Archives
- `works_ls18.csv.tar.gz` - 184K individual project records
- `works_ls17.csv.tar.gz` - 263K individual project records
- `works_rs.csv.tar.gz` - 62K individual project records

### Elections
- `elections/elections_18ls.csv` - 2024 election results with margins
- `elections/elections_17ls.csv` - 2019 election results with margins

**Competitiveness classification:**
- `safe`: margin > 15%
- `competitive`: margin 5-15%
- `marginal`: margin < 5%

### Visualizations
- `fig_01_funnel.png` - Funding funnel by tenure
- `fig_02_distributions.png` - Completion rate distributions
- `fig_03_percentiles.png` - Per-MP distribution violin plots
- `fig_04_scatter.png` - Recommended vs completed scatter
- `fig_05_margin.png` - Electoral margin analysis
- `fig_06_party.png` - Party-wise allocation
- `fig_07_incumbent.png` - Incumbent vs first-term comparison

## Key Analysis Findings

### Tenure-Level Summary

| Tenure | Allocated | Rec % | Sanc % | Expend % | Comp % |
|--------|-----------|-------|--------|----------|--------|
| 17th LS (2019-24) | Rs 4,768 Cr | 94% | 90% | 79% | 49% |
| 18th LS (2024-) | Rs 8,248 Cr | 58% | 43% | 26% | 13% |
| Rajya Sabha | Rs 3,619 Cr | 64% | 50% | 36% | 19% |

The 17th LS shows higher rates because MPs had a full 5-year term. For the 18th LS (ongoing), **expenditure (26%) is a better progress measure than completion (13%)** since works take time to finish.

### MP-Level Completion Distribution (18th Lok Sabha)

| Percentile | Completion Rate |
|------------|-----------------|
| 0th (min) | 0.0% |
| 25th | 3.4% |
| 50th (median) | 7.3% |
| 75th | 17.8% |
| 100th (max) | 66.0% |

**Completion Buckets:**
- Zero completion: 96 MPs (18%)
- 0-10%: 253 MPs
- 10-25%: 106 MPs
- 25-50%: 72 MPs
- >50%: 16 MPs (3%)

### Electoral Competitiveness Analysis

**Hypothesis:** MPs in marginal seats may complete more works to strengthen electoral position.

| Seat Type | N | Mean Completion | Median Completion |
|-----------|---|-----------------|-------------------|
| Safe (>15% margin) | 191 | 12.0% | 7.3% |
| Competitive (5-15%) | 218 | 11.9% | 6.8% |
| Marginal (<5%) | 131 | 14.8% | 8.8% |

**Correlation (margin vs completion):** r = -0.03

**Finding:** Weak relationship. Marginal seats show slightly higher completion (+2-3 percentage points), but effect is small.

### Party-wise Completion (18th Lok Sabha)

| Party | MPs | Mean Completion | Median Completion |
|-------|-----|-----------------|-------------------|
| BJP | 237 | 12.0% | 7.3% |
| INC | 99 | 9.9% | 6.8% |
| SP | 38 | 17.2% | 11.2% |
| TMC | 29 | 10.0% | 6.4% |
| DMK | 22 | 19.3% | 15.5% |

## Technical Notes

### API Architecture
The eSAKSHI portal exposes REST endpoints at `https://mplads.mospi.gov.in/rest/PreLoginDashboardData/`:
- `getStateData` - List of states
- `getConstituencyData` - Constituencies per state
- `getMpAndConstCombo` - MPs per constituency (LS)
- `getMpNamesData` - MPs per state (RS)
- `getTilesData` - Aggregate spending tiles
- `getTilesReportData` - Work-level details

**Lok Sabha API format:**
- MPs: `getMpAndConstCombo` with `const_combo = "constituency_id,2,tenure_id"`
- Tiles: `getTilesData` with `uname = "state_id,const_id,mp_id,2,tenure_id"`

**Rajya Sabha API format:**
- MPs: `getMpNamesData` with `state_combo = "state_id,1"`
- Tiles: `getTilesData` with `uname = "state_id,0,mp_id,1"` (no tenure parameter)

Requires session cookies from `/digigov/dashboard.html`.

### Caching & Resumability
Scripts use JSONL caches (`data/raw/*.jsonl`) for resumability. Re-running skips already-fetched data.

### Rate Limiting
Server rate-limits aggressively. Scripts use exponential backoff with base 10s delay and re-authenticate after multiple failures.

### Data Recency
The eSAKSHI portal (live since April 2023) only has data for FY 2023-24 onward. Historical spending for earlier years is not available.

### Data Model
Primary key is (mp_id, tenure_id, house). Same MP across tenures = separate rows.

## License

Data sourced from [eSAKSHI](https://mplads.mospi.gov.in), a Government of India portal.
