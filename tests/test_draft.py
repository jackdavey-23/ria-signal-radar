import json
from types import SimpleNamespace

import pandas as pd

from radar import draft
from radar.draft import claims_in_row, draft_openers, numbers_not_in_row

ROW = pd.Series(
    {
        "crd": 288863,
        "name": "Example Wealth",
        "city": "Atlanta",
        "state": "GA",
        "raum": 8789840000.0,
        "growth": 1.279,
        "seats": 151.0,
        "offices": 104.0,
        "hnw_share": 0.373,
        "why": "seats 151 (+20)",
    }
)


def test_validator_accepts_numbers_rendered_from_the_row():
    text = (
        "Your firm reports $8.8B in RAUM, up 128% since the prior filing, "
        "with 151 advisors across 104 offices."
    )
    assert numbers_not_in_row(text, ROW) == []


def test_total_locations_counts_as_a_row_number():
    assert numbers_not_in_row("serving clients from 105 locations", ROW) == []


def test_validator_rejects_numbers_not_in_the_row():
    assert numbers_not_in_row("$9.1B over the last 12 months", ROW) == ["9.1", "12"]
    assert claims_in_row(["$8.8B RAUM", "a top 25 list"], ROW) == ["$8.8B RAUM"]


def test_demo_mode_is_true():
    assert draft.DEMO_MODE is True


class _StubClient:
    def __init__(self, payload):
        self.messages = SimpleNamespace(
            create=lambda **kw: SimpleNamespace(
                content=[SimpleNamespace(type="text", text=json.dumps(payload))],
                usage=SimpleNamespace(input_tokens=400, output_tokens=80),
            )
        )


def test_draft_openers_marks_invalid_claims_and_prices_usage():
    top = pd.DataFrame([ROW])
    good = {
        "opener": "You report $8.8B across 104 offices.",
        "claims_used": ["$8.8B RAUM", "104 offices"],
    }
    bad = {"opener": "You crossed $9.1B this year.", "claims_used": ["$9.1B RAUM"]}
    drafts, usage = draft_openers(top, n=1, client=_StubClient(good))
    assert drafts[0]["valid"] and drafts[0]["sent"] is False
    drafts, usage = draft_openers(top, n=1, client=_StubClient(bad))
    assert not drafts[0]["valid"] and drafts[0]["rejected_numbers"] == ["9.1", "9.1"]
    assert usage["input_tokens"] == 400 and usage["cost_usd"] == round(
        400 / 1e6 * 1.0 + 80 / 1e6 * 5.0, 4
    )
