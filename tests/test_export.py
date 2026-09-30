import ast
from pathlib import Path

import pandas as pd

from radar.export import apply_suppression, domain_from_website, iapd_url, write_outputs

BANNED = {"smtplib", "imaplib", "sendgrid", "resend", "mailgun"}


def test_domain_rejects_social_and_strips_www():
    assert domain_from_website("https://www.linkedin.com/company/x") is None
    assert domain_from_website("http://www.example-wealth.com/about") == "example-wealth.com"
    assert domain_from_website("example-wealth.com") == "example-wealth.com"
    assert domain_from_website("") is None and domain_from_website(None) is None


def test_suppression_by_crd_only():
    df = pd.DataFrame({"crd": [1, 2, 3], "name": ["LaSalle St. Investment Advisors", "b", "c"]})
    kept, dropped = apply_suppression(df, [{"crd": 2, "name": "b", "reason": "customer"}])
    assert kept["crd"].tolist() == [1, 3] and dropped["crd"].tolist() == [2]


def test_iapd_url():
    assert iapd_url(288863) == "https://adviserinfo.sec.gov/firm/summary/288863"


def test_write_outputs_shapes(tmp_path):
    n = 60
    scored = pd.DataFrame(
        {
            "crd": range(1, n + 1),
            "name": [f"Firm {i}" for i in range(n)],
            "city": "Tucson",
            "state": "AZ",
            "raum": 1e9,
            "growth": 0.1,
            "seats": 20.0,
            "offices": 2.0,
            "hnw_share": 0.5,
            "score": sorted([float(i) for i in range(n)], reverse=True),
            "tier": "C",
            "why": "seats 20 (+7)",
            "item11": False,
        }
    )
    suppressed = scored.iloc[:0]
    paths = write_outputs(scored, suppressed, ["item11"], tmp_path, "run-x")
    top50 = pd.read_csv(paths["top50"])
    top25 = pd.read_csv(paths["top25"])
    assert len(top50) == 50 and top50["rank"].tolist() == list(range(1, 51))
    assert len(top25) == 25 and "your_verdict" in top25.columns
    assert (top50["run_id"] == "run-x").all() and top50["iapd_url"].str.contains(
        "adviserinfo"
    ).all()


def test_no_email_library_is_imported_anywhere():
    for path in Path("src/radar").glob("*.py"):
        tree = ast.parse(path.read_text())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {n.name.split(".")[0] for n in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
        assert not (names & BANNED), f"{path} imports {names & BANNED}"


def test_demo_mode_is_hard_coded_if_draft_exists():
    src = Path("src/radar/draft.py")
    if src.exists():
        assert "DEMO_MODE = True" in src.read_text()
