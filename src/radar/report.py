"""Static HTML report for GitHub Pages. No JavaScript framework, no API key, nothing live."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

CSS = """
:root{--bg:#fbfbfa;--fg:#1d1d1b;--muted:#6b6b66;--line:#e4e3de;--card:#fff;--acc:#2f5d8a;--a:#1f7a4d;--b:#b7791f;--c:#8a8a85}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ebebe6;--muted:#a3a39c;--line:#2f2f2c;--card:#1f1f1d;--acc:#8ab4e8;--a:#6fcf97;--b:#e0b458;--c:#8a8a85}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 10px}
.banner{background:var(--acc);color:#fff;padding:10px 14px;border-radius:8px;font-weight:600;margin:14px 0 20px}
.kpis{display:flex;gap:10px;flex-wrap:wrap}.kpi{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;min-width:140px}
.kpi b{display:block;font-size:22px}.muted{color:var(--muted)}table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);font-size:13px}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{cursor:pointer;user-select:none;white-space:nowrap}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}.tier{font-weight:700}.A{color:var(--a)}.B{color:var(--b)}.C{color:var(--c)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.wrap{overflow-x:auto}code{font-size:12px}footer{margin-top:40px;color:var(--muted);font-size:13px}
"""
JS = """
document.querySelectorAll('table.sortable th').forEach((th,i)=>th.addEventListener('click',()=>{
 const t=th.closest('table'),rows=[...t.tBodies[0].rows],num=th.classList.contains('n'),asc=!(th.dataset.asc==='1');
 rows.sort((a,b)=>{const x=a.cells[i].dataset.v??a.cells[i].textContent,y=b.cells[i].dataset.v??b.cells[i].textContent;
 return num?(asc?x-y:y-x):(asc?x.localeCompare(y):y.localeCompare(x));});rows.forEach(r=>t.tBodies[0].appendChild(r));
 t.querySelectorAll('th').forEach(h=>delete h.dataset.asc);th.dataset.asc=asc?'1':'0';}));
"""


def _money(v: float) -> str:
    return f"${v / 1e9:.1f}B" if v >= 1e9 else f"${v / 1e6:.0f}M"


def _review_cell(r: pd.Series, review: dict) -> str:
    e = review.get(int(r["crd"]))
    if e and e["decision"] == "remove":
        return f"<span class=C>removed: {html.escape(e['category'].replace('_', ' '))}</span>"
    if e and e["decision"] == "restore":
        return "<span class=A>restored: bank flag false positive</span>"
    if bool(r.get("bank_affiliate", False)):
        return "<span class=C>removed: bank affiliate (automatic)</span>"
    if e and e.get("display_name"):
        return f"kept as {html.escape(e['display_name'])}"
    return "kept" if e else ""


def _row(r: pd.Series, review: dict | None = None) -> str:
    g = "" if pd.isna(r["growth"]) else f"{r['growth']:+.0%}"
    review_td = f"<td>{_review_cell(r, review)}</td>" if review is not None else ""
    return (
        f"<tr><td class=n>{int(r['rank'])}</td><td>{html.escape(str(r['name']))}</td><td>{html.escape(str(r['state']))}</td>"
        f"<td class=n data-v='{r['raum']}'>{_money(float(r['raum']))}</td><td class=n data-v='{r['growth'] if not pd.isna(r['growth']) else -9}'>{g}</td>"
        f"<td class=n>{int(r['seats'])}</td><td class=n>{int(r['offices'])}</td><td class=n>{r['hnw_share']:.0%}</td>"
        f"<td class=n>{r['score']}</td><td class='tier {r['tier']}'>{r['tier']}</td><td>{html.escape(str(r['why']))}</td>{review_td}</tr>"
    )


def render_report(
    run_log: dict,
    top: pd.DataFrame,
    drafts: list[dict],
    preset2: dict | None,
    out: Path,
    review: dict | None = None,
) -> Path:
    rid, h = run_log["run_id"], run_log["config"]["hash"]
    tiers = run_log["tier_counts"]
    funnel = "".join(
        f"<tr><td>{f['gate']}</td><td>{html.escape(f['description'])}</td><td class=n>{f['remaining']:,}</td></tr>"
        for f in run_log["funnel"]
    )
    seeds = "".join(
        f"<li>{html.escape(s['name'])}: #{s['rank']} of {run_log['universe_size']} ({s['tier']}, {s['score']})</li>"
        for s in run_log["seed_ranks"]
    )
    sens = "".join(
        f"<tr><td>{r['factor']}</td><td class=n>{r['delta']:+d}</td><td class=n>{r['top_n_kept']} / 50</td></tr>"
        for r in run_log["sensitivity"]
    )
    rows = "".join(_row(r, review) for _, r in top.iterrows())
    review_th = "<th>Human review</th>" if review is not None else ""
    n_removed = sum(1 for e in (review or {}).values() if e["decision"] == "remove")
    review_note = (
        f"<p class=muted>Form ADV has no field for who owns a firm. A name-by-name review of the top 50 (each firm's site, ADV and news, 2026-09-30) is applied as versioned data in <code>config/hand_review.yaml</code>: bank-affiliated firms drop automatically, {n_removed} more were removed by hand (insurer captives, aggregator subsidiaries, regional brokerages, one duplicate parent), one false removal was restored. The vendor sheet is what remains.</p>"
        if review is not None
        else ""
    )
    if drafts:
        cards = "".join(
            f"<div class=card><b>{html.escape(d['name'])}</b> <span class=muted>CRD {d['crd']} · {'validated' if d['valid'] else 'REJECTED: ' + ', '.join(d['rejected_numbers'])}</span>"
            f"<p>{html.escape(d['opener'])}</p><p class=muted>claims: {html.escape('; '.join(d['claims_used']))}</p></div>"
            for d in drafts[:3]
        )
        usage = run_log.get("usage") or {}
        cost = (
            f" Cost for {len(drafts)} drafts from real usage: ${usage.get('cost_usd', 0):.4f} ({usage.get('model', '')})."
            if usage
            else ""
        )
        drafts_html = f"<p class=muted>{sum(d['valid'] for d in drafts)} of {len(drafts)} drafts passed the validator (every number must exist in the firm's own row).{cost} None were sent.</p><div class=cards>{cards}</div>"
    else:
        drafts_html = "<p class=muted>No drafts generated for this run: drafting needs an API key and is run separately with <code>uv run radar draft</code>. Nothing is ever sent.</p>"
    p2 = ""
    if preset2:
        f2 = " → ".join(f"{f['remaining']:,}" for f in preset2["funnel"])
        t2 = preset2["tier_counts"]
        p2 = f"<h2>Second preset: asset-manager distribution</h2><p>Same engine, different buyer (<code>config/icp_am_distribution.yaml</code>, run <code>{preset2['run_id']}</code>): funnel {f2}; tiers A {t2.get('A', 0)} · B {t2.get('B', 0)} · C {t2.get('C', 0)}. No public customer list exists for this buyer, so no sanity-check claim is made.</p>"
    doc = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>RIA Signal Radar</title><style>{CSS}</style></head><body><main>
<h1>RIA Signal Radar</h1><div class=muted>SEC Form ADV filings → ICP score → explained list. Run <code>{rid}</code>, config <code>{h}</code>.</div>
<div class=banner>Drafts only. Nothing is ever sent. Public firm-level data. No LinkedIn, no BrokerCheck, no vendor affiliation.</div>
<div class=kpis><div class=kpi><b>{run_log["funnel"][0]["remaining"]:,}</b><span class=muted>firms in the roster</span></div><div class=kpi><b>{run_log["universe_size"]}</b><span class=muted>in the ICP universe</span></div>
<div class=kpi><b class=A>{tiers.get("A", 0)}</b><span class=muted>tier A</span></div><div class=kpi><b class=B>{tiers.get("B", 0)}</b><span class=muted>tier B</span></div><div class=kpi><b class=C>{tiers.get("C", 0)}</b><span class=muted>tier C</span></div></div>
<h2>Funnel</h2><div class=wrap><table><thead><tr><th>Gate</th><th>Rule</th><th class=n>Remaining</th></tr></thead><tbody>{funnel}</tbody></table></div>
<h2>Top 50 (after suppression)</h2><p class=muted>Click a header to sort. The why string names the three biggest factors and any flags.</p>{review_note}
<div class=wrap><table class=sortable><thead><tr><th class=n>#</th><th>Firm</th><th>State</th><th class=n>RAUM</th><th class=n>Growth</th><th class=n>Seats</th><th class=n>Offices</th><th class=n>HNW</th><th class=n>Score</th><th>Tier</th><th>Why</th>{review_th}</tr></thead><tbody>{rows}</tbody></table></div>
<h2>Sanity check, not a backtest</h2><p>The vendor's four public customers, ranked by the frozen config (n = 4; they shaped the gates and weights):</p><ul>{seeds}</ul>
<h2>Sensitivity</h2><p class=muted>Each weight moved ±5 points; how many of the baseline top 50 remain.</p><div class=wrap><table><thead><tr><th>Factor</th><th class=n>Δ</th><th class=n>Top 50 kept</th></tr></thead><tbody>{sens}</tbody></table></div>
<h2>Drafts</h2>{drafts_html}
{p2}
<footer>Growth is annual amendment to annual amendment, not "last 12 months", and is not purchase intent. Every figure on this page is copied from <code>outputs/run_log.json</code>. Source: <a href="https://github.com/jackdavey-23/ria-signal-radar">github.com/jackdavey-23/ria-signal-radar</a>.</footer>
</main><script>{JS}</script></body></html>"""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc)
    return out
