#!/usr/bin/env python3
"""Fetch detailed work-level data for Rajya Sabha MPs.

For each RS MP, fetches the work records underlying each tile type
(Recommended, Sanctioned, Completed works).

RS-specific format:
  - No constituency - MPs are state-based
  - combo format: "state_id,0,mp_id,1"

Input: data/mplads_rs.csv (aggregate RS data)
Output: data/works_rs.csv
"""

from __future__ import annotations

import argparse
import csv
import json
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
            logger.warning(
                f"Session init attempt {attempt + 1} failed: {e}. Waiting {wait}s..."
            )
            time.sleep(wait)
    return False


def api_post(
    session: requests.Session, path: str, body: dict, delay: float = 1.0
) -> Any:
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
    ap.add_argument("--input", default="data/mplads_rs.csv")
    ap.add_argument("--cache", default="data/raw/mplads_works_rs_cache.jsonl")
    ap.add_argument("--out", default="data/works_rs.csv")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    logger.info(f"Starting RS work-level fetch at {datetime.now()}")

    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}. Run fetch_mplads_rs.py first.")
        return

    df = pd.read_csv(args.input, dtype=str).fillna("")
    if args.limit:
        df = df.head(args.limit)

    logger.info(f"Processing {len(df)} RS MPs")

    cache = JsonlCache(Path(args.cache))
    logger.info(f"Cache has {len(cache)} entries")

    session = make_session()
    if not init_session(session):
        logger.error("Failed to initialize session")
        return

    all_records: list[dict[str, Any]] = []
    all_columns: set[str] = set()

    for _, row in tqdm(list(df.iterrows()), desc="RS MPs"):
        state_id = row["state_id"]
        mp_id = row["mp_id"]
        combo = f"{state_id},0,{mp_id},1"

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

            records = []
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                for _, val in data.items():
                    if isinstance(val, str):
                        try:
                            parsed = json.loads(val)
                            if isinstance(parsed, list):
                                records.extend(parsed)
                        except json.JSONDecodeError:
                            pass
                    elif isinstance(val, list):
                        records.extend(val)

            for rec in records or []:
                if not isinstance(rec, dict):
                    continue
                flat: dict[str, Any] = {
                    "tenure_label": row.get("tenure_label", "Rajya Sabha"),
                    "house": row.get("house", "Rajya Sabha"),
                    "state_id": state_id,
                    "state_name": row.get("state_name", ""),
                    "mp_id": mp_id,
                    "mp_name": row.get("mp_name", ""),
                    "mp_tenure": row.get("mp_tenure", ""),
                    "tile_label": tile_label,
                    **{
                        k: (v.strip() if isinstance(v, str) else v)
                        for k, v in rec.items()
                    },
                }
                all_records.append(flat)
                all_columns.update(flat.keys())

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prefix = [
        "tenure_label",
        "house",
        "state_id",
        "state_name",
        "mp_id",
        "mp_name",
        "mp_tenure",
        "tile_label",
    ]
    rest = sorted(c for c in all_columns if c not in prefix)
    cols = prefix + rest

    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_records)

    logger.info(f"Done: {len(all_records)} RS work records -> {out_path}")


if __name__ == "__main__":
    main()
