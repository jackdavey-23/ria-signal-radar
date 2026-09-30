"""Download the two SEC monthly adviser roster files into data/raw/.

Usage: uv run python scripts/fetch_sec.py
SEC fair-access policy: declare a User-Agent with a contact (set SEC_CONTACT in .env), stay under
10 requests/second. This script makes two requests.
"""

from __future__ import annotations

import hashlib
import io
import os
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://www.sec.gov/files/investment/data"
FILES = {
    # Sep 2026 registered advisers (zip holding one CSV), listed on the SEC page 2026-09-29
    "ia09012026-registered.zip": (
        f"{BASE}/other/information-about-registered-investment-advisers-exempt-reporting-advisers/"
        "ia09012026-registered.zip"
    ),
    # Sep 2025 registered advisers (xlsx)
    "ia09022025.xlsx": (
        f"{BASE}/information-about-registered-investment-advisers-exempt-reporting-advisers/"
        "ia09022025.xlsx"
    ),
}
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str, contact: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": f"ria-signal-radar ({contact})"})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (fixed https host)
        return resp.read()


def main() -> None:
    contact = os.environ.get("SEC_CONTACT", "research script")
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        data = fetch(url, contact)
        if name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                member = next(m for m in zf.namelist() if m.lower().endswith(".csv"))
                out = RAW / name.replace(".zip", ".csv")
                out.write_bytes(zf.read(member))
        else:
            out = RAW / name
            out.write_bytes(data)
        digest = sha256(out.read_bytes())[:16]
        print(f"{out.name}  {out.stat().st_size:,} bytes  sha256={digest}...")


if __name__ == "__main__":
    main()
