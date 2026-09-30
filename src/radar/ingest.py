"""Typed load of the SEC monthly Form ADV roster files, driven by config/fields.yaml."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from dataclasses import fields as dc_fields
from pathlib import Path

import pandas as pd
import yaml

PRIOR_COLUMNS = ["raum", "staff", "bd_reps", "adv_staff", "private_fund", "offices"]


@dataclass(frozen=True)
class Field:
    column: str
    name: str
    type: str  # money | count | flag | text | date
    item: str = ""
    wording: str = ""
    gotcha: str = ""


def load_fields(path: Path) -> list[Field]:
    keys = {f.name for f in dc_fields(Field)}
    raw = yaml.safe_load(Path(path).read_text())["fields"]
    return [Field(**{k: v for k, v in entry.items() if k in keys}) for entry in raw]


def parse_money(value: object) -> float:
    """'   434,165,916.00' -> 434165916.0; '.00' -> 0.0; blank -> nan."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float("nan")
    s = str(value).replace(",", "").strip()
    if s in {"", "nan", "None"}:
        return float("nan")
    if s == ".00":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return float("nan")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_raw(path: Path) -> pd.DataFrame:
    """Read a roster file as strings with the original headers (headers cast to str)."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, dtype=str, encoding="latin-1", low_memory=False)
    elif suffix in {".xlsx", ".xls"}:
        cache = path.with_suffix(".cache.csv")  # the XLSX takes ~20s to read; cache it once
        if not cache.exists():
            pd.read_excel(path, dtype=str).to_csv(cache, index=False)
        df = pd.read_csv(cache, dtype=str, low_memory=False)
    else:
        raise ValueError(f"unsupported file type: {path}")
    df.columns = [str(c).strip() for c in df.columns]  # the Item 11 header is int 11 in the XLSX
    return df


def load_registered(path: Path, fields: list[Field]) -> tuple[pd.DataFrame, dict]:
    path = Path(path)
    raw = read_raw(path)
    missing = [f.column for f in fields if f.column not in raw.columns]
    if missing:
        raise KeyError(f"{path.name} is missing columns: {missing}")
    out = pd.DataFrame(index=raw.index)
    for f in fields:
        s = raw[f.column]
        if f.type == "money":
            out[f.name] = s.map(parse_money).astype("float64")
        elif f.type == "count":
            out[f.name] = pd.to_numeric(s.str.replace(",", "", regex=False), errors="coerce")
        elif f.type == "flag":
            out[f.name] = s.fillna("").str.strip().str.upper().eq("Y")
        elif f.type == "date":
            out[f.name] = pd.to_datetime(s, errors="coerce")
        else:
            out[f.name] = s.fillna("").str.strip()
    out["crd"] = out["crd"].astype("int64")
    if out["crd"].duplicated().any():
        raise ValueError(f"{path.name} has duplicate CRDs")
    info = {
        "file": path.name,
        "sha256": sha256_of(path),
        "rows": int(len(raw)),
        "columns": int(raw.shape[1]),
    }
    return out.reset_index(drop=True), info


def join_years(current: pd.DataFrame, prior: pd.DataFrame) -> pd.DataFrame:
    """Left-join last year's file on CRD; firms with no prior row are NEW_REGISTRANT."""
    p = prior[["crd", *PRIOR_COLUMNS]].rename(columns={c: f"{c}_prior" for c in PRIOR_COLUMNS})
    df = current.merge(p, on="crd", how="left", validate="one_to_one")
    df["new_registrant"] = df["raum_prior"].isna()
    return df
