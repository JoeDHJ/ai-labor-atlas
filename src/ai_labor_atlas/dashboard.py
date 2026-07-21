from __future__ import annotations

import html
import json
from pathlib import Path


def render(
    rows: list[dict[str, str]],
    summary: dict[str, object],
    groups: list[dict[str, object]],
) -> str:
    top = sorted(
        rows, key=lambda row: float(row.get("ai_exposure") or -999), reverse=True
    )[:12]
    cards = "".join(
        f"<div class='card'><b>{html.escape(str(key))}</b><span>{html.escape(str(value))}</span></div>"
        for key, value in summary.items()
        if key
        in {
            "rows",
            "exposure_coverage",
            "wage_coverage",
            "employment_weighted_exposure",
        }
    )
    table = "".join(
        f"<tr><td>{html.escape(row.get('title', ''))}</td><td>{html.escape(row.get('soc_2018_code', ''))}</td><td>{html.escape(row.get('ai_exposure', ''))}</td><td>{html.escape(row.get('median_annual_wage', ''))}</td></tr>"
        for row in top
    )
    payload = json.dumps({"summary": summary, "groups": groups}, ensure_ascii=False)
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>AI Labor Atlas</title><style>
    body{{font-family:Inter,system-ui,sans-serif;background:#f5f7fb;color:#182230;max-width:1100px;margin:32px auto;padding:0 20px}}h1{{margin-bottom:4px}}.muted{{color:#617083}}.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0}}.card{{background:white;border:1px solid #e5e9f0;border-radius:12px;padding:14px 18px;min-width:155px;box-shadow:0 2px 8px #172b4d0b}}.card b,.card span{{display:block}}.card b{{font-size:12px;color:#65748b;text-transform:uppercase}}.card span{{font-size:22px;margin-top:6px}}table{{background:white;border-collapse:collapse;width:100%;border-radius:12px;overflow:hidden}}th,td{{padding:11px 12px;border-bottom:1px solid #eef1f5;text-align:left}}th{{background:#eef3fb}}code{{background:#e9eef7;padding:2px 5px;border-radius:4px}}</style></head><body>
    <h1>AI Labor Atlas</h1><p class='muted'>Descriptive U.S. occupation, AI exposure, wage, and employment explorer. Exposure is not a causal risk score.</p>
    <section class='cards'>{cards}</section><h2>Highest exposure rows</h2><table><thead><tr><th>Occupation</th><th>2018 SOC</th><th>AI exposure</th><th>Median wage</th></tr></thead><tbody>{table}</tbody></table>
    <script type='application/json' id='atlas-data'>{html.escape(payload)}</script></body></html>"""


def write_site(
    site_dir: Path,
    rows: list[dict[str, str]],
    summary: dict[str, object],
    groups: list[dict[str, object]],
) -> Path:
    site_dir.mkdir(parents=True, exist_ok=True)
    index = site_dir / "index.html"
    index.write_text(render(rows, summary, groups), encoding="utf-8")
    return index
