from __future__ import annotations

import json
from pathlib import Path

from .llm_review import LLMReviewClient


LLM_REVIEW_CLIENT = LLMReviewClient()


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Labor Atlas | Research Explorer</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #09111f;
      --surface: #111d31;
      --surface-2: #162640;
      --surface-3: #1d3150;
      --text: #eef5ff;
      --muted: #a5b5cb;
      --line: rgba(193, 215, 245, 0.16);
      --blue: #6ea8ff;
      --cyan: #55d6c2;
      --amber: #ffc76b;
      --red: #ff8a8a;
      --shadow: 0 20px 60px rgba(0, 0, 0, 0.24);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-width: 320px;
      color: var(--text);
      background:
        radial-gradient(circle at 8% 0%, rgba(66, 133, 255, 0.23), transparent 34rem),
        radial-gradient(circle at 92% 14%, rgba(54, 211, 191, 0.13), transparent 30rem),
        var(--bg);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    .shell { width: min(1240px, calc(100% - 40px)); margin: 0 auto; padding: 34px 0 64px; }
    .topbar, .hero, .section-head, .control-row, .legend, .detail-row, .footer-row {
      display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-mark {
      width: 38px; height: 38px; border-radius: 12px;
      background: linear-gradient(135deg, var(--blue), var(--cyan));
      box-shadow: 0 8px 22px rgba(75, 190, 255, 0.28);
      position: relative;
    }
    .brand-mark::after { content: ""; position: absolute; inset: 10px; border: 2px solid #081322; border-radius: 50%; }
    .brand-name { font-weight: 700; letter-spacing: -0.02em; }
    .eyebrow, .label, .micro { color: var(--muted); font-size: 0.74rem; letter-spacing: 0.08em; text-transform: uppercase; }
    .eyebrow { color: var(--cyan); font-weight: 700; }
    h1, h2, h3, p { margin-top: 0; }
    h1 { max-width: 790px; margin-bottom: 12px; font-size: clamp(2.1rem, 5vw, 4.45rem); line-height: 1.02; letter-spacing: -0.055em; }
    h2 { font-size: clamp(1.35rem, 2.5vw, 2rem); letter-spacing: -0.035em; margin-bottom: 8px; }
    h3 { margin-bottom: 6px; font-size: 1.05rem; }
    .hero { align-items: end; padding: 74px 0 44px; }
    .hero-copy { max-width: 820px; }
    .hero-copy > p { max-width: 690px; color: var(--muted); font-size: 1.08rem; }
    .hero-badge {
      display: inline-flex; gap: 8px; align-items: center; margin-bottom: 18px;
      color: var(--cyan); background: rgba(85, 214, 194, 0.1); border: 1px solid rgba(85, 214, 194, 0.25);
      border-radius: 999px; padding: 7px 11px; font-size: 0.78rem; font-weight: 700;
    }
    .hero-badge::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--cyan); box-shadow: 0 0 14px var(--cyan); }
    .kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 28px; }
    .kpi, .panel, .meaning {
      background: linear-gradient(145deg, rgba(27, 48, 80, 0.92), rgba(13, 27, 48, 0.88));
      border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow);
    }
    .kpi { padding: 18px; min-height: 128px; }
    .kpi-value { display: block; margin: 9px 0 4px; font-size: clamp(1.45rem, 3vw, 2.15rem); font-weight: 700; letter-spacing: -0.04em; }
    .kpi-context, .muted { color: var(--muted); }
    .kpi-context { font-size: 0.82rem; }
    .panel { padding: 24px; }
    .section { margin-top: 28px; }
    .section-head { align-items: end; margin-bottom: 14px; }
    .section-head p { max-width: 640px; margin-bottom: 0; color: var(--muted); }
    .control-row { justify-content: flex-end; margin-bottom: 14px; }
    label { color: var(--muted); font-size: 0.78rem; }
    select, input, button {
      font: inherit; color: var(--text); border: 1px solid var(--line); border-radius: 10px;
      background: rgba(8, 18, 33, 0.72); padding: 9px 11px; outline: none;
    }
    select:focus, input:focus, button:focus { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(85, 214, 194, 0.16); }
    input { min-width: min(280px, 70vw); }
    button { cursor: pointer; background: var(--blue); border-color: transparent; color: #071323; font-weight: 700; }
    button.secondary { color: var(--text); background: transparent; border-color: var(--line); }
    .chart-layout { display: grid; grid-template-columns: minmax(0, 1.8fr) minmax(260px, 0.7fr); gap: 18px; align-items: start; }
    .chart-wrap { min-width: 0; }
    svg { display: block; width: 100%; height: auto; overflow: visible; }
    .chart-svg { min-height: 430px; }
    .grid-line { stroke: var(--line); stroke-width: 1; }
    .axis-label, .tick-label { fill: var(--muted); font-size: 12px; }
    .axis-title { fill: var(--muted); font-size: 13px; font-weight: 600; }
    .bubble { fill: var(--blue); fill-opacity: 0.76; stroke: var(--bg); stroke-width: 2; cursor: pointer; transition: cx 360ms ease, cy 360ms ease, r 360ms ease, fill 180ms ease, fill-opacity 180ms ease; }
    .bubble:hover, .bubble.selected { fill: var(--cyan); fill-opacity: 1; }
    .bubble.selected { stroke: var(--text); stroke-width: 3; }
    .bubble-label { fill: var(--text); font-size: 11px; pointer-events: none; }
    .detail-panel { min-height: 360px; }
    .detail-name { margin: 8px 0 4px; font-size: 1.42rem; line-height: 1.15; }
    .code-pill { display: inline-flex; color: var(--cyan); background: rgba(85, 214, 194, 0.1); border: 1px solid rgba(85, 214, 194, 0.24); padding: 4px 8px; border-radius: 8px; font-size: 0.78rem; }
    .detail-list { display: grid; gap: 10px; margin: 24px 0; }
    .detail-row { padding-bottom: 9px; border-bottom: 1px solid var(--line); }
    .detail-row strong { font-size: 1.06rem; }
    .interpretation { color: var(--muted); font-size: 0.9rem; }
    .review-panel { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--line); }
    .review-panel[hidden] { display: none; }
    .review-status { margin: 10px 0 0; color: var(--muted); font-size: 0.78rem; }
    .review-summary { margin: 14px 0 0; color: var(--text); font-size: 0.88rem; }
    .review-evidence { display: grid; gap: 8px; margin: 14px 0 0; padding: 0; list-style: none; }
    .review-evidence li { padding: 10px 12px; color: var(--muted); background: rgba(85, 214, 194, 0.08); border-left: 2px solid var(--cyan); font-size: 0.8rem; }
    .legend { justify-content: flex-start; margin-top: 10px; color: var(--muted); font-size: 0.8rem; }
    .legend-dot { display: inline-block; width: 10px; height: 10px; margin-right: 5px; border-radius: 50%; background: var(--blue); }
    .meaning-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .meaning { padding: 19px; box-shadow: none; background: rgba(17, 29, 49, 0.72); }
    .meaning p { margin-bottom: 0; color: var(--muted); font-size: 0.9rem; }
    .source-note { margin-top: 28px; color: var(--muted); font-size: 0.82rem; }
    .source-note code { color: var(--cyan); }
    .footer-row { margin-top: 42px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.8rem; }
    @media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .chart-layout { grid-template-columns: 1fr; } }
    @media (max-width: 620px) { .shell { width: min(100% - 26px, 1240px); } .hero { padding-top: 48px; } .kpi-grid, .meaning-grid { grid-template-columns: 1fr; } .panel { padding: 17px; } .chart-svg { min-height: 330px; } }
    @media (prefers-reduced-motion: reduce) { .bubble { transition: none; } }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span><span class="brand-name">AI Labor Atlas</span></div>
      <span class="micro">Descriptive research explorer</span>
    </header>
    <section class="hero">
      <div class="hero-copy">
        <div class="hero-badge">U.S. occupations | task-level evidence</div>
        <h1>Where does AI overlap with work?</h1>
        <p>This explorer connects occupational tasks, an AI exposure indicator, wages, employment, and projections. It helps you ask better questions about changing work - it does not forecast layoffs.</p>
      </div>
    </section>
    <section class="kpi-grid" aria-label="Atlas overview">
      <article class="kpi"><span class="label">Occupations</span><strong class="kpi-value" id="kpi-rows">Not available</strong><span class="kpi-context">occupations included</span></article>
      <article class="kpi"><span class="label">Exposure coverage</span><strong class="kpi-value" id="kpi-exposure">Not available</strong><span class="kpi-context">occupations with an exposure value</span></article>
      <article class="kpi"><span class="label">Employment-weighted exposure</span><strong class="kpi-value" id="kpi-weighted">Not available</strong><span class="kpi-context">larger occupations count more</span></article>
      <article class="kpi"><span class="label">Wage coverage</span><strong class="kpi-value" id="kpi-wage">Not available</strong><span class="kpi-context">occupations with a wage estimate</span></article>
    </section>
    <section class="section">
      <div class="section-head">
        <div><span class="eyebrow">Read the map</span><h2>Exposure, economic position, and scale</h2></div>
        <p>Move between outcomes to see how the same exposure measure relates to different descriptive questions.</p>
      </div>
      <div class="panel">
        <div class="control-row">
          <label for="metric-select">Y-axis
            <select id="metric-select">
              <option value="wage">Median annual wage</option>
              <option value="growth">Projected employment growth</option>
              <option value="openings">Annual openings</option>
            </select>
          </label>
          <label for="occupation-search">Search occupations
            <input id="occupation-search" type="search" placeholder="e.g. software">
          </label>
          <button id="reset-view" class="secondary" type="button">Reset view</button>
        </div>
        <div class="chart-layout">
          <div class="chart-wrap">
            <svg id="atlas-chart" class="chart-svg" viewBox="0 0 820 440" role="img" aria-labelledby="chart-title chart-desc">
              <title id="chart-title">Occupation AI exposure comparison</title>
              <desc id="chart-desc">Bubble chart comparing AI exposure with an economic outcome. Bubble area represents employment.</desc>
              <g id="grid"></g><g id="marks"></g><g id="labels"></g>
              <text class="axis-title" x="430" y="426" text-anchor="middle">AI exposure</text>
              <text id="y-axis-title" class="axis-title" transform="translate(18 220) rotate(-90)" text-anchor="middle">Median annual wage</text>
            </svg>
            <div class="legend"><span><span class="legend-dot"></span>Bubble area = employment</span><span>Click a bubble to inspect an occupation</span></div>
          </div>
          <aside class="detail-panel">
            <span class="eyebrow">Selected occupation</span>
            <h3 class="detail-name" id="detail-title">Select an occupation</h3>
            <span class="code-pill" id="detail-code">—</span>
            <div class="detail-list">
              <div class="detail-row"><span class="muted">AI exposure</span><strong id="detail-exposure">—</strong></div>
              <div class="detail-row"><span class="muted" id="detail-outcome-label">Median wage</span><strong id="detail-outcome">—</strong></div>
              <div class="detail-row"><span class="muted">Employment</span><strong id="detail-employment">—</strong></div>
              <div class="detail-row"><span class="muted">Projected change</span><strong id="detail-growth">—</strong></div>
            </div>
            <p class="interpretation" id="detail-interpretation">Select an occupation to see a plain-language interpretation.</p>
            <div class="review-panel">
              <button id="deep-review-button" type="button" disabled>Review this mapping</button>
              <p class="review-status" id="deep-review-status">Optional review available when enabled.</p>
              <div id="deep-review-result" hidden>
                <p class="review-summary" id="deep-review-summary"></p>
                <ul class="review-evidence" id="deep-review-evidence"></ul>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Economic meaning</span><h2>What the numbers can and cannot say</h2></div></div>
      <div class="meaning-grid">
        <article class="meaning"><h3>AI exposure ≠ job loss</h3><p>The exposure field measures overlap between occupational tasks and AI capabilities. It is an applicability signal, not a probability of displacement.</p></article>
        <article class="meaning"><h3>Wage is a level</h3><p>A wage comparison describes where occupations sit in the labor market. It does not show that AI exposure causes a wage difference.</p></article>
        <article class="meaning"><h3>Projections are a baseline</h3><p>Employment projections summarize a published scenario. They help frame scale and direction, but do not isolate the effect of AI.</p></article>
      </div>
      <p class="source-note">Source note: The dashboard combines occupational task information, AI exposure estimates, and wage, employment, and projection data. Missing values remain visible rather than being treated as zero.</p>
    </section>
    <footer class="footer-row"><span>Occupational evidence for clearer questions about changing work.</span><span>Descriptive analysis, not a forecast of individual job outcomes.</span></footer>
  </main>
  <script id="atlas-data" type="application/json">__ATLAS_DATA__</script>
  <script>
    (function () {
      const payload = JSON.parse(document.getElementById("atlas-data").textContent);
      const rows = payload.rows || [];
      const summary = payload.summary || {};
      const chart = document.getElementById("atlas-chart");
      const grid = document.getElementById("grid");
      const marks = document.getElementById("marks");
      const labels = document.getElementById("labels");
      const metricSelect = document.getElementById("metric-select");
      const search = document.getElementById("occupation-search");
      const reset = document.getElementById("reset-view");
      const deepReviewButton = document.getElementById("deep-review-button");
      const deepReviewStatus = document.getElementById("deep-review-status");
      const deepReviewResult = document.getElementById("deep-review-result");
      const deepReviewSummary = document.getElementById("deep-review-summary");
      const deepReviewEvidence = document.getElementById("deep-review-evidence");
      const llmEnabled = __LLM_ENABLED__;
      const yAxisTitle = document.getElementById("y-axis-title");
      const selected = { index: 0 };
      const ns = "http://www.w3.org/2000/svg";
      const numeric = function (value) { const result = Number(value); return Number.isFinite(result) ? result : null; };
      const money = function (value) { return value == null ? "Not available" : "$" + Math.round(value).toLocaleString("en-US"); };
      const percent = function (value) { return value == null ? "Not available" : value.toFixed(1) + "%"; };
      const workers = function (value) {
        if (value == null) return "Not available";
        return value >= 1000000 ? (value / 1000000).toFixed(2) + "M" : Math.round(value / 1000).toLocaleString("en-US") + "K";
      };
      const metric = {
        wage: { label: "Median annual wage", axis: "Median annual wage", field: "median_annual_wage", format: money, note: "This is a descriptive wage level. A higher value does not mean AI exposure caused higher pay." },
        growth: { label: "Projected growth", axis: "Projected employment growth", field: "employment_change_2024_2034_pct", format: percent, note: "This is a projected change under the source scenario. It is not an AI causal effect." },
        openings: { label: "Annual openings", axis: "Annual openings", field: "annual_openings_2024_2034", format: workers, note: "Annual openings capture replacement and growth demand. They are not the same as net new jobs." }
      };
      const make = function (tag, attrs, text) {
        const node = document.createElementNS(ns, tag);
        Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
        if (text != null) node.textContent = text;
        return node;
      };
      const setText = function (id, value) { document.getElementById(id).textContent = value; };
      const htmlNode = function (tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = text;
        return node;
      };
      function renderDeepReview(review) {
        deepReviewResult.hidden = false;
        deepReviewSummary.textContent = (review.decision || "review") + " · " + Math.round(Number(review.confidence || 0) * 100) + "% confidence. " + (review.rationale || "No rationale supplied.");
        deepReviewEvidence.innerHTML = "";
        (review.evidence || []).forEach(function (item) { deepReviewEvidence.appendChild(htmlNode("li", "", item)); });
      }
      async function deepReview() {
        const selectedRow = rows[selected.index] || {};
        if (!selectedRow.title) { deepReviewStatus.textContent = "Select an occupation before requesting a review."; return; }
        deepReviewButton.disabled = true;
        deepReviewStatus.textContent = "Reviewing the supplied occupation evidence…";
        try {
          const response = await fetch("/api/deep-review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ occupation: selectedRow, candidates: [selectedRow] }) });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || "review unavailable");
          renderDeepReview(payload);
          deepReviewStatus.textContent = "Review complete. Treat review flags as prompts for verification.";
        } catch (error) { deepReviewStatus.textContent = "Review unavailable. The descriptive result remains available."; }
        finally { deepReviewButton.disabled = !llmEnabled; }
      }
      const filteredRows = function () {
        const query = search.value.trim().toLowerCase();
        return rows.map(function (row, index) { return { row: row, index: index }; }).filter(function (item) {
          return !query || String(item.row.title || "").toLowerCase().includes(query);
        });
      };
      function updateKpis() {
        setText("kpi-rows", Number(summary.rows || 0).toLocaleString("en-US"));
        setText("kpi-exposure", ((Number(summary.exposure_coverage || 0)) * 100).toFixed(1) + "%");
        setText("kpi-weighted", numeric(summary.employment_weighted_exposure) == null ? "Not available" : Number(summary.employment_weighted_exposure).toFixed(2));
        setText("kpi-wage", ((Number(summary.wage_coverage || 0)) * 100).toFixed(1) + "%");
      }
      function draw() {
        const currentMetric = metric[metricSelect.value];
        const visible = filteredRows();
        if (visible.length && !visible.some(function (item) { return item.index === selected.index; })) selected.index = visible[0].index;
        const exposureValues = visible.map(function (item) { return numeric(item.row.ai_exposure); }).filter(function (value) { return value != null; });
        const outcomeValues = visible.map(function (item) { return numeric(item.row[currentMetric.field]); }).filter(function (value) { return value != null; });
        const xMax = Math.max(1, Math.ceil((Math.max.apply(null, exposureValues.length ? exposureValues : [1]) * 1.08) * 10) / 10);
        let yMin = Math.min.apply(null, outcomeValues.length ? outcomeValues : [0]);
        let yMax = Math.max.apply(null, outcomeValues.length ? outcomeValues : [1]);
        if (yMin === yMax) { yMin -= 1; yMax += 1; }
        const yPad = (yMax - yMin) * 0.08;
        yMin -= yPad; yMax += yPad;
        const x = function (value) { return 78 + (value / xMax) * 670; };
        const y = function (value) { return 350 - ((value - yMin) / (yMax - yMin)) * 286; };
        const employmentValues = rows.map(function (row) { return numeric(row.employment_2024) || 0; });
        const maxEmployment = Math.max.apply(null, employmentValues.length ? employmentValues : [1]);
        grid.innerHTML = "";
        const ticks = 5;
        for (let i = 0; i <= ticks; i += 1) {
          const xTick = (xMax / ticks) * i;
          const yTick = yMin + ((yMax - yMin) / ticks) * i;
          grid.appendChild(make("line", { class: "grid-line", x1: x(xTick), x2: x(xTick), y1: 64, y2: 350 }));
          grid.appendChild(make("text", { class: "tick-label", x: x(xTick), y: 371, "text-anchor": "middle" }, xTick.toFixed(1)));
          grid.appendChild(make("line", { class: "grid-line", x1: 78, x2: 748, y1: y(yTick), y2: y(yTick) }));
          const yText = currentMetric.field === "median_annual_wage" ? "$" + Math.round(yTick / 1000) + "k" : currentMetric.field === "annual_openings_2024_2034" ? Math.round(yTick / 1000) + "k" : yTick.toFixed(0) + "%";
          grid.appendChild(make("text", { class: "tick-label", x: 68, y: y(yTick) + 4, "text-anchor": "end" }, yText));
        }
        marks.innerHTML = ""; labels.innerHTML = "";
        visible.forEach(function (item) {
          const row = item.row;
          const exposure = numeric(row.ai_exposure);
          const outcome = numeric(row[currentMetric.field]);
          if (exposure == null || outcome == null) return;
          const circle = make("circle", {
            class: "bubble" + (item.index === selected.index ? " selected" : ""),
            cx: x(exposure), cy: y(outcome),
            r: 7 + Math.sqrt((numeric(row.employment_2024) || 0) / maxEmployment) * 24,
            "aria-label": String(row.title || "Occupation")
          });
          circle.addEventListener("click", function () { selected.index = item.index; draw(); });
          marks.appendChild(circle);
          const label = String(row.title || "").replace(" and ", " & ");
          const text = make("text", { class: "bubble-label", x: x(exposure) + 9, y: y(outcome) + 4 }, label);
          labels.appendChild(text);
        });
        yAxisTitle.textContent = currentMetric.axis;
        const selectedRow = rows[selected.index] || {};
        setText("detail-title", selectedRow.title || "Select an occupation");
        setText("detail-code", selectedRow.soc_2018_code || "SOC unavailable");
        setText("detail-exposure", numeric(selectedRow.ai_exposure) == null ? "Not available" : numeric(selectedRow.ai_exposure).toFixed(2));
        setText("detail-outcome-label", currentMetric.label);
        setText("detail-outcome", currentMetric.format(numeric(selectedRow[currentMetric.field])));
        setText("detail-employment", workers(numeric(selectedRow.employment_2024)));
        setText("detail-growth", percent(numeric(selectedRow.employment_change_2024_2034_pct)));
        setText("detail-interpretation", selectedRow.title ? currentMetric.note : "Select an occupation to see a plain-language interpretation.");
        deepReviewButton.disabled = !llmEnabled || !selectedRow.title;
        deepReviewResult.hidden = true;
        deepReviewSummary.textContent = "";
        deepReviewEvidence.innerHTML = "";
      }
      metricSelect.addEventListener("change", draw);
      search.addEventListener("input", draw);
      deepReviewButton.addEventListener("click", deepReview);
      reset.addEventListener("click", function () { search.value = ""; metricSelect.value = "wage"; selected.index = 0; draw(); });
      if (llmEnabled) deepReviewStatus.textContent = "Optional review available.";
      updateKpis(); draw();
    }());
  </script>
</body>
</html>
"""


def render(
    rows: list[dict[str, str]],
    summary: dict[str, object],
    groups: list[dict[str, object]],
) -> str:
    del groups
    payload = json.dumps(
        {"rows": rows, "summary": summary},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")
    return HTML_TEMPLATE.replace("__ATLAS_DATA__", payload).replace(
        "__LLM_ENABLED__", json.dumps(LLM_REVIEW_CLIENT.config.enabled)
    )


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
