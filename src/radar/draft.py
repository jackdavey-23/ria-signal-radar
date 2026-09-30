"""Claude-drafted openers for the top firms. Drafts are exported to a file and never sent.

Every number in an opener must be a rendering of a number in the firm's own row; the validator
rejects the rest. Run: `uv run radar draft` (needs ANTHROPIC_API_KEY in .env; refuses otherwise).
"""

from __future__ import annotations

import json
import re

import pandas as pd

DEMO_MODE = True  # no send path exists in this package; tests/test_export.py enforces it
MODEL = "claude-haiku-4-5"  # picked in the plan for cost: ~50 short drafts
PRICE_PER_MTOK = {"input": 1.00, "output": 5.00}  # claude-api skill model table, cached 2026-09-25
ROSTER_YEARS = {"2025", "2026"}
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
FACT_COLUMNS = (
    "raum",
    "growth",
    "seats",
    "offices",
    "staff",
    "bd_reps",
    "adv_staff",
    "hnw_share",
    "hnw_clients",
    "hybrid_depth",
)
NEVER_MENTION = {"item11"}
# Flags are described in words with no digits, so the validator never has to whitelist them.
FLAG_PHRASES = {
    "new_registrant": "new SEC registrant this year",
    "stale_filing": "latest Form ADV filing is from a prior year",
    "crossed_500m": "crossed half a billion dollars in AUM between the last two annual filings",
    "crossed_1b": "crossed one billion dollars in AUM between the last two annual filings",
    "crossed_5b": "crossed five billion dollars in AUM between the last two annual filings",
    "fund_launched": "began advising a private fund since the prior filing",
    "bank_affiliate": "affiliated with a bank or thrift",
    "seat_growth": "advisor headcount grew by a fifth or more since the prior filing",
    "low_discretion": "less than half of assets are managed on a discretionary basis",
    "commissions": "compensated partly by commissions",
    "manager_selection": "selects outside managers for clients",
    "bd_linked": "linked to a broker-dealer",
}

SYSTEM = (
    "You draft one short, plain cold-email opener (at most 70 words) from a wealth-technology "
    "vendor's outreach associate to a registered investment adviser, using only the facts "
    "provided. No greeting line, no flattery, no filler such as 'significant opportunities' or "
    "'streamline'. One specific observation from the facts, then one short question. Never "
    "mention regulatory or disciplinary disclosures, never invent, round or recompute a number "
    "beyond what is given, never name the vendor. Return JSON with the opener and the list of "
    "factual claims you used, each claim quoting the figure exactly as given."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "opener": {"type": "string"},
        "claims_used": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["opener", "claims_used"],
    "additionalProperties": False,
}


def _renderings(v: float) -> set[str]:
    """Every way a prompt or a model might legitimately write this number."""
    forms = {
        f"{v:.0f}",
        f"{v:.1f}",
        f"{v:.2f}",
        f"{v / 1e6:.0f}",
        f"{v / 1e6:.1f}",
        f"{v / 1e9:.1f}",
        f"{v / 1e9:.2f}",
        f"{v * 100:.0f}",
        f"{v * 100:.1f}",
    }
    return {f.replace(",", "").lstrip("-") for f in forms}


def allowed_numbers(row: pd.Series) -> set[str]:
    out = set(ROSTER_YEARS)
    for col in FACT_COLUMNS:
        v = row.get(col)
        if v is not None and not pd.isna(v):
            out |= _renderings(float(v))
    offices = row.get("offices")
    if offices is not None and not pd.isna(offices):
        out.add(f"{float(offices) + 1:.0f}")  # total locations = principal office + others
    return out


def numbers_not_in_row(text: str, row: pd.Series) -> list[str]:
    ok = allowed_numbers(row)
    return [t for t in (m.replace(",", "") for m in NUMBER.findall(text)) if t not in ok]


def claims_in_row(claims: list[str], row: pd.Series) -> list[str]:
    return [c for c in claims if not numbers_not_in_row(c, row)]


def _money(v: float) -> str:
    return f"${v / 1e9:.1f}B" if v >= 1e9 else f"${v / 1e6:.0f}M"


def firm_facts(row: pd.Series, flags: list[str]) -> str:
    lines = [
        f"Firm: {row['name']} ({row.get('city', '')}, {row.get('state', '')})",
        f"Regulatory assets under management (Form ADV 5F(2)(c)): {_money(float(row['raum']))}",
    ]
    if not pd.isna(row.get("growth")):
        lines.append(f"Change in AUM versus the prior annual filing: {float(row['growth']):+.0%}")
    lines.append(f"Advisor seats (larger of 5B(1) and 5B(2)): {float(row['seats']):.0f}")
    offices = float(row["offices"])
    lines.append(
        f"Locations: {offices + 1:.0f} in total (the principal office plus {offices:.0f} others)"
    )
    lines.append(f"High-net-worth share of AUM: {float(row['hnw_share']):.0%}")
    fired = [
        FLAG_PHRASES.get(f, f)
        for f in flags
        if f not in NEVER_MENTION and f in FLAG_PHRASES and bool(row.get(f, False))
    ]
    if fired:
        lines.append("Signals: " + "; ".join(fired))
    return "\n".join(lines)


def draft_openers(
    top: pd.DataFrame, n: int = 50, client=None, model: str = MODEL, flags: list[str] | None = None
) -> tuple[list[dict], dict]:
    if client is None:
        from anthropic import Anthropic  # imported here so tests never need the SDK or a key

        client = Anthropic()
    drafts: list[dict] = []
    usage = {"model": model, "input_tokens": 0, "output_tokens": 0}
    for _, row in top.head(n).iterrows():
        resp = client.messages.create(
            model=model,
            max_tokens=400,
            system=SYSTEM,
            messages=[{"role": "user", "content": firm_facts(row, flags or [])}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
        data = json.loads(next(b.text for b in resp.content if b.type == "text"))
        bad = numbers_not_in_row(data["opener"], row)
        for claim in data["claims_used"]:
            bad += numbers_not_in_row(claim, row)
        usage["input_tokens"] += resp.usage.input_tokens
        usage["output_tokens"] += resp.usage.output_tokens
        drafts.append(
            {
                "crd": int(row["crd"]),
                "name": row["name"],
                "opener": data["opener"],
                "claims_used": data["claims_used"],
                "valid": not bad,
                "rejected_numbers": bad,
                "sent": False,
            }
        )
    usage["cost_usd"] = round(
        usage["input_tokens"] / 1e6 * PRICE_PER_MTOK["input"]
        + usage["output_tokens"] / 1e6 * PRICE_PER_MTOK["output"],
        4,
    )
    return drafts, usage
