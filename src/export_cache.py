#!/usr/bin/env python3
"""Export MPLADS cache to CSV.

Reads from a JSONL cache file and exports MP-level spending data to CSV.

Usage:
    uv run python src/export_cache.py --cache data/raw/mplads_17ls_cache.jsonl --out data/mplads_17ls.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from _client import JsonlCache


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


def parse_tiles(data: dict) -> dict:
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

STATE_NAMES_18LS = {
    "35": "Andaman And Nicobar Islands",
    "2": "Andhra Pradesh",
    "3": "Arunachal Pradesh",
    "4": "Assam",
    "5": "Bihar",
    "36": "Chandigarh",
    "6": "Chhattisgarh",
    "38": "Dadra And Nagar Haveli And Daman And Diu",
    "7": "Delhi",
    "8": "Goa",
    "9": "Gujarat",
    "10": "Haryana",
    "11": "Himachal Pradesh",
    "12": "Jammu And Kashmir",
    "13": "Jharkhand",
    "14": "Karnataka",
    "15": "Kerala",
    "37": "Ladakh",
    "39": "Lakshadweep",
    "16": "Madhya Pradesh",
    "17": "Maharashtra",
    "18": "Manipur",
    "19": "Meghalaya",
    "20": "Mizoram",
    "21": "Nagaland",
    "22": "Odisha",
    "40": "Puducherry",
    "23": "Punjab",
    "24": "Rajasthan",
    "25": "Sikkim",
    "26": "Tamil Nadu",
    "27": "Telangana",
    "28": "Tripura",
    "29": "Uttar Pradesh",
    "30": "Uttarakhand",
    "31": "West Bengal",
}

STATE_NAMES_17LS = {
    "1": "Punjab",
    "2": "Andhra Pradesh",
    "3": "Arunachal Pradesh",
    "5": "Assam",
    "6": "Bihar",
    "7": "Chandigarh",
    "8": "Chhattisgarh",
    "11": "Delhi",
    "12": "Goa",
    "13": "Mizoram",
    "14": "Haryana",
    "15": "Himachal Pradesh",
    "16": "Jammu And Kashmir",
    "17": "Jharkhand",
    "18": "Karnataka",
    "19": "Lakshadweep",
    "20": "Madhya Pradesh",
    "21": "Maharashtra",
    "22": "Manipur",
    "23": "Meghalaya",
    "24": "Nagaland",
    "25": "Odisha",
    "26": "Puducherry",
    "27": "Gujarat",
    "28": "Rajasthan",
    "29": "Sikkim",
    "30": "Tamil Nadu",
    "35": "Andaman And Nicobar Islands",
    "36": "Kerala",
    "130": "Ladakh",
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Export MPLADS cache to CSV")
    ap.add_argument("--cache", required=True, help="Path to JSONL cache file")
    ap.add_argument("--out", help="Output CSV path (defaults to data/<cache_name>.csv)")
    args = ap.parse_args()

    cache_path = Path(args.cache)
    if not cache_path.exists():
        print(f"Cache file not found: {cache_path}")
        return

    cache = JsonlCache(cache_path)
    print(f"Loaded cache with {len(cache)} entries")

    # Build state/const/mp lookups from cache
    states = {}
    constituencies = {}
    mps = {}
    tiles = {}

    for key, value in cache.items():
        if key.startswith("const|"):
            state_id = key.split("|")[1]
            constituencies[state_id] = value
        elif key.startswith("mp|"):
            parts = key.split("|")
            const_id, house, tenure_id = parts[1], parts[2], parts[3]
            mps[(const_id, house, tenure_id)] = value
        elif key.startswith("tiles|"):
            parts = key.split("|")
            state_id, const_id, mp_id, house, tenure_id = parts[1:6]
            tiles[(state_id, const_id, mp_id, house, tenure_id)] = value

    # Detect tenure to use correct state name mapping
    tenure_id = None
    for key, _ in cache.items():
        if key.startswith("tiles|"):
            parts = key.split("|")
            tenure_id = parts[5]
            break

    if tenure_id == "5":
        states = STATE_NAMES_17LS.copy()
    else:
        states = STATE_NAMES_18LS.copy()

    # Build rows from tiles
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

    # Build constituency lookup
    const_names = {}
    for state_id, consts in constituencies.items():
        for c in consts:
            const_names[str(c["ID"])] = c["CAPTION"].strip()

    # Build MP lookup
    mp_names = {}
    for (const_id, house, tenure_id), mp_list in mps.items():
        for m in mp_list:
            mp_names[str(m["ID"])] = m["CAPTION"].strip() if m.get("CAPTION") else ""

    for (state_id, const_id, mp_id, house, tenure_id), tile_data in tiles.items():
        tenure_label = TENURE_LABELS.get(tenure_id, f"Tenure {tenure_id}")
        house_name = "Lok Sabha" if house == "2" else "Rajya Sabha"

        row = {
            "tenure_label": tenure_label,
            "tenure_id": tenure_id,
            "house": house_name,
            "state_id": state_id,
            "state_name": states.get(state_id, ""),
            "constituency_id": const_id,
            "constituency_name": const_names.get(const_id, ""),
            "mp_id": mp_id,
            "mp_name": mp_names.get(mp_id, ""),
        }

        if tile_data:
            row.update(parse_tiles(tile_data))

        # Only include rows with actual data
        if row.get("allocated_cr") is not None or row.get("recommended_cr") is not None:
            rows.append(row)

    if not rows:
        print("No MP data found in cache")
        return

    # Determine output path
    if args.out:
        out_path = Path(args.out)
    else:
        cache_name = cache_path.stem.replace("_cache", "")
        out_path = Path("data") / f"{cache_name}.csv"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"Exported {len(rows)} MPs to {out_path}")


if __name__ == "__main__":
    main()
