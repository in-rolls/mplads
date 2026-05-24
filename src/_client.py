"""Shared HTTP client for the MPLADS dashboard.

Centralises session creation, retries, throttling, and a JSONL cache so
scripts can be re-run without re-hitting the upstream APIs.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MPLADS_BASE = "https://mplads.mospi.gov.in"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class Throttle:
    """Sleep between calls with jitter to be polite to public APIs."""

    base_seconds: float = 0.5
    jitter: float = 0.3

    def wait(self) -> None:
        time.sleep(self.base_seconds + random.random() * self.jitter)


def make_mplads_session() -> requests.Session:
    """Session pre-seeded with cookies from the dashboard page."""
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
    retry = Retry(
        total=6,
        backoff_factor=1.5,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.get(f"{MPLADS_BASE}/digigov/dashboard.html", timeout=30)
    return s


def mplads_post(
    session: requests.Session,
    path: str,
    body: dict[str, Any],
    throttle: Throttle | None = None,
    timeout: int = 60,
) -> Any:
    """POST JSON to an MPLADS REST endpoint and return the parsed response."""
    if throttle is not None:
        throttle.wait()
    url = f"{MPLADS_BASE}{path}"
    r = session.post(url, json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()


class JsonlCache:
    """Append-only JSONL cache keyed by a stable string.

    Each line is {"key": <str>, "value": <json>}. On load we keep only the last
    value seen for a given key, which lets you overwrite a bad cached row by
    re-running with a fresh request.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._mem: dict[str, Any] = {}
        if self.path.exists():
            with self.path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    self._mem[rec["key"]] = rec["value"]

    def __contains__(self, key: str) -> bool:
        return key in self._mem

    def get(self, key: str) -> Any:
        return self._mem.get(key)

    def put(self, key: str, value: Any) -> None:
        self._mem[key] = value
        with self.path.open("a") as f:
            f.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")

    def items(self) -> list[tuple[str, Any]]:
        return list(self._mem.items())

    def __len__(self) -> int:
        return len(self._mem)
