#!/usr/bin/env python3
"""Fetch detailed work-level data for each MP.

For each MP, fetches the work records underlying each tile type
(Recommended, Sanctioned, Completed works).

Input: data/mplads_full.csv from fetch_mplads.py
Output:
  data/raw/mplads_works_cache.jsonl   cache for resumability
  data/interim/mplads_works.csv       flat work-level data
"""

from __future__ import annotations

import argparse
import csv
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.exceptions import ConnectionError, RequestException, Timeout
from tqdm import tqdm

from _client import MPLADS_BASE, UA, JsonlCache

MAX_RETRIES = 5
BACKOFF_BASE = 10.0

TILE_LABELS = [
    "Works Recommended",
    "Works Sanctioned",
    "Works Completed",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": MPLADS_BASE,
            "Referer": f"{MPLADS_BASE}/digigov/dashboard.html",
        }
    )
    return s


def init_session(session: requests.Session) -> bool:
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(f"{MPLADS_BASE}/digigov/dashboard.html", timeout=30)
            r.raise_for_status()
            return True
        except (ConnectionError, Timeout, RequestException) as e:
            wait = BACKOFF_BASE * (2**attempt)
            logger.warning(f"Session init attempt {attempt + 1} failed: {e}. Waiting {wait}s...")
            time.sleep(wait)
    return False


def api_post(session: requests.Session, path: str, body: dict, delay: float = 1.0) -> Any:
    time.sleep(delay)
    for attempt in range(MAX_RETRIES):
        try:
            r = session.post(f"{MPLADS_BASE}{path}", json=body, timeout=60)
            r.raise_for_status()
            return r.json()
        except (ConnectionError, Timeout, RequestException) as e:
            wait = BACKOFF_BASE * (2**attempt)
            logger.warning(
                f"API call failed ({path}): {e}. Retry {attempt + 1}/{MAX_RETRIES} in {wait}s..."
            )
            time.sleep(wait)
            if attempt >= 2:
                init_session(session)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/mplads_full.csv")
    ap.add_argument("--cache", default="data/raw/mplads_works_cache.jsonl")
    ap.add_argument("--out", default="data/interim/mplads_works.csv")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    logger.info(f"Starting work-level fetch at {datetime.now()}")

    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}. Run fetch_mplads.py first.")
        return

    df = pd.read_csv(args.input, dtype=str).fillna("")
    if args.limit:
        df = df.head(args.limit)

    logger.info(f"Processing {len(df)} MPs")

    cache = JsonlCache(Path(args.cache))
    logger.info(f"Cache has {len(cache)} entries")

    session = make_session()
    if not init_session(session):
        logger.error("Failed to initialize session")
        return

    all_records: list[dict[str, Any]] = []
    all_columns: set[str] = set()

    for _, row in tqdm(list(df.iterrows()), desc="MPs"):
        state_id = row["state_id"]
        const_id = row["constituency_id"]
        mp_id = row["mp_id"]
        house = "2" if row.get("house", "") == "Lok Sabha" else "1"
        tenure_id = row["tenure_id"]
        combo = f"{state_id},{const_id},{mp_id},{house},{tenure_id}"

        for tile_label in TILE_LABELS:
            cache_key = f"{combo}||{tile_label}"
            if cache_key in cache:
                data = cache.get(cache_key)
            else:
                data = api_post(
                    session,
                    "/rest/PreLoginDashboardData/getTilesReportData",
                    {"combo": combo, "key": tile_label},
                    args.delay,
                )
                if data is not None:
                    cache.put(cache_key, data)

            if not data:
                continue

            records = data if isinstance(data, list) else data.get("data", [])
            for rec in records or []:
                if not isinstance(rec, dict):
                    continue
                flat: dict[str, Any] = {
                    "tenure_id": tenure_id,
                    "house": row.get("house", ""),
                    "state_id": state_id,
                    "state_name": row.get("state_name", ""),
                    "constituency_id": const_id,
                    "constituency_name": row.get("constituency_name", ""),
                    "mp_id": mp_id,
                    "mp_name": row.get("mp_name", ""),
                    "tile_label": tile_label,
                    **{k: (v.strip() if isinstance(v, str) else v) for k, v in rec.items()},
                }
                all_records.append(flat)
                all_columns.update(flat.keys())

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = [
        "tenure_id",
        "house",
        "state_id",
        "state_name",
        "constituency_id",
        "constituency_name",
        "mp_id",
        "mp_name",
        "tile_label",
    ]
    rest = sorted(c for c in all_columns if c not in prefix)
    cols = prefix + rest
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_records)

    logger.info(f"Done: {len(all_records)} work records -> {out_path}")


if __name__ == "__main__":
    main()
