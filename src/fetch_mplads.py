#!/usr/bin/env python3
"""Unified MPLADS data fetcher - gets MP info AND spending tiles in one pass.

For each MP, fetches:
1. Basic info (name, constituency, state)
2. All 6 spending tiles (allocated, recommended, sanctioned, completed, etc.)

Output:
  data/mplads_full.csv - One row per MP with all spending data
  data/raw/mplads_full_cache.jsonl - Cache for resumability
"""

from __future__ import annotations

import argparse
import csv
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout
from tqdm import tqdm

from _client import MPLADS_BASE, UA, JsonlCache

MAX_RETRIES = 5
BACKOFF_BASE = 10.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def make_session() -> requests.Session:
    """Create session with cookies from dashboard page."""
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
    """Initialize session cookies by hitting dashboard."""
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
    """POST to MPLADS API with retries."""
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


def parse_amount(raw: str | None) -> float | None:
    """Parse amount string to crores."""
    if raw is None:
        return None
    s = str(raw).replace("\u20b9", "").replace("Rs", "").replace(",", "").strip()
    is_crore = False
    for unit in ("Crore", "Cr", "crore", "cr"):
        if s.endswith(unit):
            s = s[: -len(unit)].strip()
            is_crore = True
            break
    if not s:
        return None
    try:
        val = float(s)
        if not is_crore and val > 100:
            val = val / 10_000_000
        return round(val, 4)
    except ValueError:
        return None


def parse_tiles(data: dict) -> dict[str, Any]:
    """Parse tiles response into flat dict."""
    result = {}
    label_map = {
        "Allocated Limit for": ("allocated_cr", "n_allocated"),
        "Works Recommended": ("recommended_cr", "n_recommended"),
        "Works Sanctioned": ("sanctioned_cr", "n_sanctioned"),
        "Works Completed": ("completed_cr", "n_completed"),
        "Expenditure on Completed and On-going Works as on Date": (
            "expenditure_cr",
            "n_expenditure",
        ),
        "Amount consented for Calamity": ("calamity_cr", "n_calamity"),
    }

    for label, val in data.items():
        if label == "Current Tenure":
            continue
        if not isinstance(val, list) or not val:
            continue

        for prefix, (amt_col, n_col) in label_map.items():
            if prefix.lower() in label.lower():
                if len(val) >= 2:
                    result[n_col] = (
                        val[0] if not isinstance(val[0], str) or not val[0].endswith("Cr") else None
                    )
                    result[amt_col] = parse_amount(val[1] if len(val) > 1 else val[0])
                else:
                    result[amt_col] = parse_amount(val[0])
                break

    return result


TENURE_LABELS = {
    "7": "18th Lok Sabha",
    "5": "17th Lok Sabha",
    "6": "Rajya Sabha 2024",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/mplads_full.csv")
    ap.add_argument("--cache", default="data/raw/mplads_full_cache.jsonl")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--tenure-id", default="7", help="7=18th LS, 5=17th LS")
    ap.add_argument("--house", type=int, default=2, help="2=LS, 1=RS")
    args = ap.parse_args()

    logger.info(f"Starting MPLADS fetch at {datetime.now()}")
    logger.info(f"Tenure: {args.tenure_id}, House: {args.house}")

    cache = JsonlCache(Path(args.cache))
    logger.info(f"Cache has {len(cache)} entries")

    session = make_session()
    if not init_session(session):
        logger.error("Failed to initialize session")
        return

    # Get states
    states = api_post(session, "/rest/PreLoginDashboardData/getStateData", {}, args.delay)
    if not states:
        logger.error("Failed to fetch states")
        return
    logger.info(f"Found {len(states)} states")

    tenure_label = TENURE_LABELS.get(args.tenure_id, f"Tenure {args.tenure_id}")

    rows = []
    cols = [
        "tenure_label",
        "tenure_id",
        "house",
        "state_id",
        "state_name",
        "constituency_id",
        "constituency_name",
        "mp_id",
        "mp_name",
        "allocated_cr",
        "recommended_cr",
        "sanctioned_cr",
        "completed_cr",
        "expenditure_cr",
        "calamity_cr",
        "n_recommended",
        "n_sanctioned",
        "n_completed",
    ]

    for state in tqdm(states, desc="States"):
        state_id = str(state["STATE_ID"])
        state_name = state["STATE_NAME"].strip()

        # Get constituencies for this state
        const_key = f"const|{state_id}"
        if const_key in cache:
            constituencies = cache.get(const_key)
        else:
            constituencies = api_post(
                session,
                "/rest/PreLoginDashboardData/getConstituencyData",
                {"id": state_id},
                args.delay,
            )
            if constituencies:
                cache.put(const_key, constituencies)

        if not constituencies:
            logger.warning(f"No constituencies for {state_name}")
            continue

        for const in constituencies:
            if not const.get("CAPTION"):
                continue
            const_id = str(const["ID"])
            const_name = const["CAPTION"].strip()

            # Get MPs for this constituency
            mp_key = f"mp|{const_id}|{args.house}|{args.tenure_id}"
            if mp_key in cache:
                mps = cache.get(mp_key)
            else:
                mps = api_post(
                    session,
                    "/rest/PreLoginDashboardData/getMpAndConstCombo",
                    {"const_combo": f"{const_id},{args.house},{args.tenure_id}"},
                    args.delay,
                )
                if mps is not None:
                    cache.put(mp_key, mps)

            if not mps:
                continue

            for mp in mps:
                mp_id = str(mp["ID"])
                mp_name = (mp["CAPTION"] or "").strip()

                # Get tiles for this MP
                tile_key = f"tiles|{state_id}|{const_id}|{mp_id}|{args.house}|{args.tenure_id}"
                if tile_key in cache:
                    tiles_data = cache.get(tile_key)
                else:
                    combo = f"{state_id},{const_id},{mp_id},{args.house},{args.tenure_id}"
                    tiles_data = api_post(
                        session,
                        "/rest/PreLoginDashboardData/getTilesData",
                        {"uname": combo},
                        args.delay,
                    )
                    if tiles_data is not None:
                        cache.put(tile_key, tiles_data)

                row = {
                    "tenure_label": tenure_label,
                    "tenure_id": args.tenure_id,
                    "house": "Lok Sabha" if args.house == 2 else "Rajya Sabha",
                    "state_id": state_id,
                    "state_name": state_name,
                    "constituency_id": const_id,
                    "constituency_name": const_name,
                    "mp_id": mp_id,
                    "mp_name": mp_name,
                }

                if tiles_data:
                    row.update(parse_tiles(tiles_data))

                rows.append(row)
                logger.info(f"Got {mp_name} ({const_name}): {row.get('allocated_cr', 'N/A')} Cr")

    # Save
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    logger.info(f"Done: {len(rows)} MPs -> {out_path}")


if __name__ == "__main__":
    main()
