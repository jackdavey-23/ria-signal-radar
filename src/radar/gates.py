"""Hard filters from config, with the surviving count logged after each one."""

from __future__ import annotations

import pandas as pd


def apply_gates(df: pd.DataFrame, gates: list[dict]) -> tuple[pd.DataFrame, list[dict]]:
    funnel = [{"gate": "all", "description": "rows in file", "remaining": int(len(df))}]
    kept = df
    for g in gates:
        kept = kept.query(g["expr"], engine="python")
        funnel.append(
            {"gate": g["id"], "description": g["description"], "remaining": int(len(kept))}
        )
    return kept, funnel
