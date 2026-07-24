from __future__ import annotations

import json
from pathlib import Path

from .llm_review import LLMReviewClient
from .metrics import aggregate_onet_rows


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
    .kpi-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-bottom: 28px; }
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
    .bubble:hover, .bubble.selected, .bubble:focus { fill: var(--cyan); fill-opacity: 1; }
    .bubble:focus { outline: none; stroke: var(--text); stroke-width: 3; }
    .bubble.selected { stroke: var(--text); stroke-width: 3; }
    .bubble-label { fill: var(--text); font-size: 11px; pointer-events: none; }
    .detail-panel, .task-panel, .task-list { min-width: 0; }
    .detail-panel { min-height: 360px; }
    .detail-name { margin: 8px 0 4px; font-size: 1.42rem; line-height: 1.15; }
    .code-pill { display: inline-flex; color: var(--cyan); background: rgba(85, 214, 194, 0.1); border: 1px solid rgba(85, 214, 194, 0.24); padding: 4px 8px; border-radius: 8px; font-size: 0.78rem; }
    .detail-mapping { margin: 8px 0 0; color: var(--muted); font-size: .76rem; line-height: 1.4; }
    .detail-list { display: grid; gap: 10px; margin: 24px 0; }
    .detail-row { padding-bottom: 9px; border-bottom: 1px solid var(--line); }
    .detail-row strong { font-size: 1.06rem; }
    .interpretation { color: var(--muted); font-size: 0.9rem; }
    .task-panel { margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--line); }
    .task-title { margin: 8px 0 4px; font-size: 1.05rem; }
    .task-note { margin-bottom: 10px; color: var(--muted); font-size: 0.78rem; }
    .task-filter-label { display: block; margin: 4px 0 5px; color: var(--muted); font-size: 0.76rem; }
    .task-filter-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(120px, 138px); gap: 9px; margin: 0 0 12px; }
    .task-filter { width: 100%; min-width: 0; margin: 0; }
    .task-list { display: grid; gap: 8px; margin: 0; padding-left: 18px; color: var(--muted); font-size: 0.82rem; }
    .task-list li::marker { color: var(--cyan); }
    .task-caveat { margin: 13px 0 0; color: var(--muted); font-size: 0.74rem; }
    .bridge-controls { display: flex; align-items: end; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }
    .bridge-controls label { display: grid; gap: 6px; min-width: min(420px, 100%); }
    .bridge-controls select { width: 100%; }
    .bridge-source { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--line); }
    .bridge-source strong { display: block; margin-top: 4px; font-size: 1.18rem; }
    .bridge-source-meta { color: var(--muted); font-size: .78rem; }
    .bridge-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .bridge-card { display: grid; gap: 10px; padding: 16px; background: rgba(8, 18, 33, .48); border: 1px solid var(--line); border-radius: 15px; }
    .bridge-rank { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: .72rem; letter-spacing: .07em; text-transform: uppercase; }
    .bridge-card h3 { margin-bottom: 0; font-size: 1rem; }
    .bridge-metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 7px; }
    .bridge-metric { padding: 8px; background: rgba(170, 190, 215, .08); border-radius: 9px; }
    .bridge-metric span { display: block; color: var(--muted); font-size: .65rem; }
    .bridge-metric strong { display: block; margin-top: 2px; font-size: .92rem; }
    .bridge-evidence { margin: 0; padding-left: 17px; color: var(--muted); font-size: .78rem; }
    .bridge-evidence li::marker { color: var(--cyan); }
    .bridge-hint { margin: 0; color: var(--text); font-size: .8rem; }
    .bridge-confidence { color: var(--muted); font-size: .72rem; }
    .bridge-method { margin-top: 16px; padding-top: 14px; color: var(--muted); border-top: 1px solid var(--line); font-size: .76rem; }
    .bridge-section[hidden] { display: none; }
    .review-panel { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--line); }
    .review-panel[hidden] { display: none; }
    .review-status { margin: 10px 0 0; color: var(--muted); font-size: 0.78rem; }
    .review-summary { margin: 14px 0 0; color: var(--text); font-size: 0.88rem; }
    .review-evidence { display: grid; gap: 8px; margin: 14px 0 0; padding: 0; list-style: none; }
    .review-evidence li { padding: 10px 12px; color: var(--muted); background: rgba(85, 214, 194, 0.08); border-left: 2px solid var(--cyan); font-size: 0.8rem; }
    .worker-review-panel { margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--line); }
    .worker-review-summary { margin: 6px 0 12px; color: var(--muted); font-size: 0.78rem; }
    .worker-review-filter-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 10px 0 12px; }
    .worker-review-filter-row label { display: grid; gap: 5px; color: var(--muted); font-size: 0.7rem; }
    .worker-review-filter-row select { width: 100%; min-width: 0; padding: 7px 8px; font-size: 0.76rem; }
    .worker-review-list { display: grid; gap: 10px; }
    .worker-review-card { padding: 12px; background: rgba(8, 18, 33, 0.48); border: 1px solid var(--line); border-radius: 12px; }
    .worker-review-meta { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; color: var(--muted); font-size: 0.7rem; }
    .worker-review-card blockquote { margin: 9px 0 0; color: var(--text); font-size: 0.82rem; line-height: 1.45; }
    .worker-review-tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 9px; }
    .worker-review-tag { padding: 3px 7px; color: var(--cyan); background: rgba(85, 214, 194, 0.08); border: 1px solid rgba(85, 214, 194, 0.2); border-radius: 999px; font-size: 0.68rem; }
    .worker-review-source { color: var(--cyan); }
    .worker-review-empty { margin: 0; color: var(--muted); font-size: 0.8rem; }
    .review-disclosure { margin-top: 13px; color: var(--muted); font-size: 0.72rem; }
    .review-disclosure summary { cursor: pointer; color: var(--muted); }
    .review-disclosure p { max-width: 520px; margin: 8px 0 0; line-height: 1.45; }
    .dataset-notice { margin: 0 0 18px; padding: 10px 12px; color: var(--amber); background: rgba(255, 199, 107, .1); border: 1px solid rgba(255, 199, 107, .35); border-radius: 10px; font-size: .8rem; }
    .dataset-notice:empty { display: none; }
    .legend { justify-content: flex-start; margin-top: 10px; color: var(--muted); font-size: 0.8rem; }
    .legend-dot { display: inline-block; width: 10px; height: 10px; margin-right: 5px; border-radius: 50%; background: var(--blue); }
    .meaning-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .meaning { padding: 19px; box-shadow: none; background: rgba(17, 29, 49, 0.72); }
    .meaning p { margin-bottom: 0; color: var(--muted); font-size: 0.9rem; }
    .source-note { margin-top: 28px; color: var(--muted); font-size: 0.82rem; }
    .source-note code { color: var(--cyan); }
    .footer-row { margin-top: 42px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.8rem; }
    @media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
    @media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .chart-layout { grid-template-columns: 1fr; } .bridge-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 620px) { .shell { width: min(100% - 26px, 1240px); } .hero { padding-top: 48px; } .kpi-grid, .meaning-grid, .bridge-grid { grid-template-columns: 1fr; } .task-filter-row { grid-template-columns: 1fr; } .panel { padding: 17px; } .chart-svg { min-height: 330px; } }
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
    <div class="dataset-notice" role="status">__DATASET_NOTICE__</div>
    <section class="kpi-grid" aria-label="Atlas overview">
      <article class="kpi"><span class="label">O*NET occupations</span><strong class="kpi-value" id="kpi-rows">Not available</strong><span class="kpi-context">one record per O*NET occupation after mapping aggregation</span></article>
      <article class="kpi"><span class="label">Exposure coverage</span><strong class="kpi-value" id="kpi-exposure">Not available</strong><span class="kpi-context">aggregated occupations with an exposure value</span></article>
      <article class="kpi"><span class="label">SOC-employment-weighted exposure</span><strong class="kpi-value" id="kpi-weighted">Not available</strong><span class="kpi-context">unique 2018 SOC units; shared mappings are deduplicated</span></article>
      <article class="kpi"><span class="label">Wage coverage</span><strong class="kpi-value" id="kpi-wage">Not available</strong><span class="kpi-context">occupations with a wage estimate</span></article>
      <article class="kpi"><span class="label">Task coverage</span><strong class="kpi-value" id="kpi-tasks">Not available</strong><span class="kpi-context">occupations with task examples</span></article>
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
            <div class="legend"><span><span class="legend-dot"></span>Bubble area = O*NET-mapped employment</span><span>Click or focus a bubble, then press Enter or Space to inspect an occupation</span></div>
            <p class="source-note">Each point is one aggregated O*NET occupation. Bubble size is an O*NET view; a shared SOC target may appear in more than one point and is not a unique-SOC total.</p>
          </div>
          <aside class="detail-panel">
            <span class="eyebrow">Selected occupation</span>
            <h3 class="detail-name" id="detail-title">Select an occupation</h3>
            <span class="code-pill" id="detail-code">—</span>
            <p class="detail-mapping" id="detail-mapping">SOC mapping details will appear after selection.</p>
            <div class="detail-list">
              <div class="detail-row"><span class="muted">AI exposure</span><strong id="detail-exposure">—</strong></div>
              <div class="detail-row"><span class="muted" id="detail-outcome-label">Median wage</span><strong id="detail-outcome">—</strong></div>
              <div class="detail-row"><span class="muted">Employment</span><strong id="detail-employment">—</strong></div>
              <div class="detail-row"><span class="muted">Projected change</span><strong id="detail-growth">—</strong></div>
            </div>
            <p class="interpretation" id="detail-interpretation">Select an occupation to see a plain-language interpretation.</p>
            <div class="task-panel">
              <span class="eyebrow">Work examples</span>
              <h3 class="task-title">What this occupation does</h3>
              <p class="task-note" id="task-note">Select an occupation to see example task statements.</p>
              <label class="task-filter-label" for="task-filter">Filter task statements</label>
              <div class="task-filter-row">
                <input class="task-filter" id="task-filter" type="search" placeholder="e.g. analyze or coordinate" />
                <select class="task-filter" id="task-type-filter" aria-label="Task type filter"><option value="all">All task types</option><option value="Core">Core tasks</option><option value="Supplemental">Supplemental tasks</option></select>
              </div>
              <ul class="task-list" id="task-list"></ul>
              <p class="task-caveat">Source: O*NET 30.3. These are representative work activities, not individual job requirements.</p>
            </div>
            <div class="worker-review-panel">
              <span class="eyebrow">Workplace signals</span>
              <h3 class="task-title">What workers say</h3>
              <p class="worker-review-summary" id="worker-review-summary">No public review context is loaded for this occupation yet.</p>
              <div class="worker-review-filter-row">
                <label for="worker-review-source-filter">Source
                  <select id="worker-review-source-filter"><option value="all">All sources</option></select>
                </label>
                <label for="worker-review-topic-filter">Topic
                  <select id="worker-review-topic-filter"><option value="all">All topics</option></select>
                </label>
              </div>
              <div class="worker-review-list" id="worker-review-list"></div>
              <details class="review-disclosure">
                <summary>About these reviews</summary>
                <p id="worker-review-disclosure">Reviews are user-generated and may be incomplete, subjective, outdated, or biased. They are not verified facts or representative of all workers. Source links and dates are shown where available.</p>
              </details>
            </div>
            <div class="review-panel">
              <button id="deep-review-button" type="button" disabled>Review this mapping</button>
              <p class="review-status" id="deep-review-status">Optional review available when enabled. If enabled, it sends the selected occupation and mapping to the configured endpoint.</p>
              <div id="deep-review-result" hidden>
                <p class="review-summary" id="deep-review-summary"></p>
                <ul class="review-evidence" id="deep-review-evidence"></ul>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
    <section class="section bridge-section" id="bridge-section">
      <div class="section-head"><div><span class="eyebrow">Career bridge</span><h2>Where could this work lead?</h2></div><p>Explore adjacent occupations through structured work profiles, shared tools, and representative tasks.</p></div>
      <div class="panel">
        <div class="bridge-controls">
          <label for="bridge-select">Starting occupation
            <select id="bridge-select" aria-label="Starting occupation"></select>
          </label>
          <span class="status" id="bridge-status" aria-live="polite">Select an occupation to explore a descriptive pathway.</span>
        </div>
        <div id="bridge-source" class="bridge-source"></div>
        <div id="bridge-grid" class="bridge-grid"></div>
        <p id="bridge-method" class="bridge-method"></p>
      </div>
    </section>
    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Economic meaning</span><h2>What the numbers can and cannot say</h2></div></div>
      <div class="meaning-grid">
        <article class="meaning"><h3>AI exposure ≠ job loss</h3><p>The exposure field measures overlap between occupational tasks and AI capabilities. It is an applicability signal, not a probability of displacement.</p></article>
        <article class="meaning"><h3>Wage is a level</h3><p>A wage comparison describes where occupations sit in the labor market. It does not show that AI exposure causes a wage difference.</p></article>
        <article class="meaning"><h3>Projections are a baseline</h3><p>Employment projections summarize a published scenario. They help frame scale and direction, but do not isolate the effect of AI.</p></article>
      </div>
      <p class="source-note">Source note: The dashboard combines occupational task information, AI exposure estimates, and wage, employment, and projection data. Missing values remain visible rather than being treated as zero. When one O*NET occupation maps to multiple SOC codes, occupation-level reference metrics use the disclosed crosswalk weights; the employment-weighted exposure KPI uses each unique 2018 SOC target once and the selected occupation shows any mapping warning.</p>
    </section>
    <footer class="footer-row"><span>Occupational evidence for clearer questions about changing work.</span><span>Descriptive analysis, not a forecast of individual job outcomes.</span></footer>
  </main>
  <script id="atlas-data" type="application/json">__ATLAS_DATA__</script>
  <script>
    (function () {
      const payload = JSON.parse(document.getElementById("atlas-data").textContent);
      const rows = payload.rows || [];
      const tasksByOnet = payload.tasks_by_onet || {};
      const reviewsByOnet = payload.reviews_by_onet || {};
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
      const taskNote = document.getElementById("task-note");
      const taskFilter = document.getElementById("task-filter");
      const taskTypeFilter = document.getElementById("task-type-filter");
      const taskList = document.getElementById("task-list");
      const workerReviewSummary = document.getElementById("worker-review-summary");
      const workerReviewList = document.getElementById("worker-review-list");
      const workerReviewDisclosure = document.getElementById("worker-review-disclosure");
      const workerReviewSourceFilter = document.getElementById("worker-review-source-filter");
      const workerReviewTopicFilter = document.getElementById("worker-review-topic-filter");
      const bridgeSelect = document.getElementById("bridge-select");
      const bridgeStatus = document.getElementById("bridge-status");
      const bridgeSource = document.getElementById("bridge-source");
      const bridgeGrid = document.getElementById("bridge-grid");
      const bridgeMethod = document.getElementById("bridge-method");
      const llmEnabled = __LLM_ENABLED__;
      const yAxisTitle = document.getElementById("y-axis-title");
      const detailMapping = document.getElementById("detail-mapping");
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
      const renderTasks = function (occupation) {
        taskList.innerHTML = "";
        const tasks = tasksByOnet[occupation.onet_soc_code] || [];
        const query = taskFilter.value.trim().toLowerCase();
        const taskType = taskTypeFilter.value;
        const filteredTasks = tasks.filter(function (task) {
          return (!query || task.task_statement.toLowerCase().includes(query))
            && (taskType === "all" || task.task_type === taskType);
        });
        if (!tasks.length) {
          taskNote.textContent = "No task statements are available for this occupation in the selected source release.";
          return;
        }
        if (!filteredTasks.length) {
          taskNote.textContent = "No task statements match this filter.";
          return;
        }
        const hasFilter = query || taskType !== "all";
        taskNote.textContent = (hasFilter ? filteredTasks.length + " matching" : tasks.length) + " source task statements; showing the first four examples.";
        filteredTasks.slice(0, 4).forEach(function (task) {
          const item = document.createElement("li");
          item.textContent = task.task_statement;
          taskList.appendChild(item);
        });
      };
      const htmlNode = function (tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = text;
        return node;
      };
      const reviewSourceLabel = function (value) {
        return { user_submitted: "User submitted", reddit: "Reddit", indeed: "Indeed", other: "Other public source" }[value] || "Public source";
      };
      const reviewScopeLabel = function (value) {
        return { occupation: "Occupation context", employer_role: "Employer and role", job_posting: "Specific job posting" }[value] || "Scope not specified";
      };
      const reviewTopicLabel = function (value) {
        return { pay_benefits: "Pay and benefits", interview_management: "Interview and management", work_environment: "Work environment", workload: "Workload", growth: "Growth", tasks_tools: "Tasks and tools", other: "Other" }[value] || value;
      };
      function renderWorkerReviews(occupation) {
        workerReviewList.innerHTML = "";
        const context = reviewsByOnet[occupation.onet_soc_code] || {};
        const reviews = context.reviews || [];
        const sourceLabels = context.source_labels || {};
        const topicLabels = context.topic_labels || {};
        workerReviewDisclosure.textContent = context.disclosure || "Reviews are user-generated and may be incomplete, subjective, outdated, or biased. They are not verified facts or representative of all workers. Source links and dates are shown where available.";
        const sourceValue = workerReviewSourceFilter.value;
        const topicValue = workerReviewTopicFilter.value;
        workerReviewSourceFilter.innerHTML = "";
        const allSources = htmlNode("option", "", "All sources"); allSources.value = "all"; workerReviewSourceFilter.appendChild(allSources);
        Object.keys(context.source_counts || {}).forEach(function (value) {
          workerReviewSourceFilter.appendChild(htmlNode("option", "", sourceLabels[value] || reviewSourceLabel(value))).value = value;
        });
        workerReviewTopicFilter.innerHTML = "";
        const allTopics = htmlNode("option", "", "All topics"); allTopics.value = "all"; workerReviewTopicFilter.appendChild(allTopics);
        Object.keys(context.topic_counts || {}).forEach(function (value) {
          workerReviewTopicFilter.appendChild(htmlNode("option", "", topicLabels[value] || reviewTopicLabel(value))).value = value;
        });
        workerReviewSourceFilter.value = sourceValue || "all";
        workerReviewTopicFilter.value = topicValue || "all";
        if (!reviews.length) {
          workerReviewSourceFilter.disabled = true;
          workerReviewTopicFilter.disabled = true;
          workerReviewSummary.textContent = "No public review context is loaded for this occupation yet.";
          workerReviewList.appendChild(htmlNode("p", "worker-review-empty", "When available, this space keeps different work experiences together with their source, date, and scope."));
          return;
        }
        workerReviewSourceFilter.disabled = false;
        workerReviewTopicFilter.disabled = false;
        const filteredReviews = reviews.filter(function (review) {
          return (sourceValue === "all" || !sourceValue || review.source === sourceValue)
            && (topicValue === "all" || !topicValue || (review.topics || []).includes(topicValue));
        });
        const totalReviewCount = Number(context.total_review_count || reviews.length);
        const totalText = totalReviewCount > reviews.length ? " of " + totalReviewCount : "";
        workerReviewSummary.textContent = filteredReviews.length + totalText + " public comment" + (totalReviewCount === 1 ? "" : "s") + " shown. There is no overall occupation rating.";
        if (context.is_truncated) workerReviewSummary.textContent += " The display is limited to the most recent " + reviews.length + ".";
        if (!filteredReviews.length) {
          workerReviewList.appendChild(htmlNode("p", "worker-review-empty", "No comments match these filters. Try showing all sources and topics."));
          return;
        }
        filteredReviews.slice(0, 3).forEach(function (review) {
          const card = htmlNode("article", "worker-review-card");
          const meta = htmlNode("div", "worker-review-meta");
          const source = review.source_url ? document.createElement("a") : htmlNode("span", "worker-review-source");
          source.className = "worker-review-source";
          source.textContent = reviewSourceLabel(review.source);
          if (review.source_url) { source.href = review.source_url; source.target = "_blank"; source.rel = "noreferrer"; }
          const details = [reviewScopeLabel(review.review_scope), review.review_date || "Date not provided"];
          if (review.rating != null) details.push("Rating " + review.rating + "/5");
          if (review.author_display) details.push("By " + review.author_display);
          meta.append(source, htmlNode("span", "", details.join(" · ")));
          card.appendChild(meta);
          const contextLine = [review.job_title, review.employer, review.location].filter(Boolean).join(" · ");
          if (contextLine) card.appendChild(htmlNode("p", "worker-review-meta", contextLine));
          card.appendChild(document.createElement("blockquote")).textContent = review.excerpt;
          const tags = htmlNode("div", "worker-review-tags");
          (review.topics || []).forEach(function (topic) { tags.appendChild(htmlNode("span", "worker-review-tag", topicLabels[topic] || reviewTopicLabel(topic))); });
          if (tags.childNodes.length) card.appendChild(tags);
          workerReviewList.appendChild(card);
        });
      }
      const bridgePercent = function (value) { return value == null ? "Not available" : Math.round(Number(value) * 100) + "%"; };
      const bridgeMetric = function (label, value) {
        const node = htmlNode("div", "bridge-metric");
        node.append(htmlNode("span", "", label), htmlNode("strong", "", value));
        return node;
      };
      function renderBridge(result) {
        bridgeSource.innerHTML = ""; bridgeGrid.innerHTML = ""; bridgeMethod.textContent = "";
        if (!result || !result.available) {
          bridgeStatus.textContent = result && result.message ? result.message : "Structured occupation profiles are not available in this build.";
          bridgeGrid.appendChild(htmlNode("p", "task-note", "Add the O*NET 30.3 structured files to explore occupation bridges."));
          return;
        }
        const source = result.source || {};
        const sourceCopy = htmlNode("div", "");
        sourceCopy.append(htmlNode("span", "eyebrow", "Starting point"), htmlNode("strong", "", source.title || "Occupation"), htmlNode("span", "bridge-source-meta", (source.profile_source === "family_average" ? "Family-average O*NET profile" : "Exact O*NET profile") + " · " + (source.onet_soc_code || "Code unavailable")));
        const sourceStats = htmlNode("div", "bridge-source-meta");
        sourceStats.textContent = "Wage " + money(source.median_annual_wage) + " · Projected change " + percent(source.employment_change_2024_2034_pct);
        bridgeSource.append(sourceCopy, sourceStats);
        (result.candidates || []).forEach(function (item, index) {
          const occupation = item.occupation || {};
          const card = htmlNode("article", "bridge-card");
          const rank = htmlNode("div", "bridge-rank"); rank.append(htmlNode("span", "", "Bridge " + (index + 1)), htmlNode("span", "", (item.confidence || "Limited") + " evidence"));
          card.append(rank, htmlNode("h3", "", occupation.title || "Adjacent occupation"));
          const metrics = htmlNode("div", "bridge-metrics");
          metrics.append(bridgeMetric("Profile similarity", bridgePercent(item.structured_similarity)), bridgeMetric("Software overlap", bridgePercent(item.software_overlap)), bridgeMetric("Task evidence", bridgePercent(item.task_similarity)));
          card.append(metrics);
          const labor = htmlNode("p", "bridge-source-meta", "Wage " + money(occupation.median_annual_wage) + " · Openings " + workers(occupation.annual_openings_2024_2034) + " · Growth " + percent(occupation.employment_change_2024_2034_pct));
          card.append(labor);
          const evidence = htmlNode("ul", "bridge-evidence");
          const shared = item.shared_task_evidence || [];
          if (!shared.length) evidence.appendChild(htmlNode("li", "", "No short shared-task example was identified."));
          shared.forEach(function (statement) { evidence.appendChild(htmlNode("li", "", statement)); });
          card.append(evidence, htmlNode("p", "bridge-hint", item.training_hint || "Use the shared tasks to choose a focused work sample."));
          bridgeGrid.appendChild(card);
        });
        bridgeMethod.textContent = (result.method && result.method.interpretation ? result.method.interpretation + " " : "") + (result.method && result.method.primary ? result.method.primary : "");
        bridgeStatus.textContent = "Showing " + (result.candidates || []).length + " descriptive pathway options from " + (result.candidate_count || 0).toLocaleString("en-US") + " profiled occupations.";
      }
      async function loadBridge(code) {
        bridgeStatus.textContent = "Loading the structured occupation bridge…";
        try {
          const response = await fetch("/api/bridge?source=" + encodeURIComponent(code));
          const result = await response.json();
          if (!response.ok) throw new Error(result.message || "bridge unavailable");
          renderBridge(result);
        } catch (error) {
          bridgeStatus.textContent = "The bridge is unavailable. The occupation explorer remains available.";
          bridgeGrid.innerHTML = "";
        }
      }
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
        setText("kpi-rows", Number(summary.aggregated_onet_occupation_count || summary.unique_onet_occupation_count || 0).toLocaleString("en-US"));
        setText("kpi-exposure", ((Number(summary.exposure_coverage || 0)) * 100).toFixed(1) + "%");
        setText("kpi-weighted", numeric(summary.employment_weighted_exposure) == null ? "Not available" : Number(summary.employment_weighted_exposure).toFixed(2));
        setText("kpi-wage", ((Number(summary.wage_coverage || 0)) * 100).toFixed(1) + "%");
        setText("kpi-tasks", ((Number(summary.task_occupation_coverage || 0)) * 100).toFixed(1) + "%");
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
        const showLabels = visible.length <= 24;
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
            role: "button",
            tabindex: "0",
            "aria-pressed": item.index === selected.index ? "true" : "false",
            "aria-label": "Select " + String(row.title || "Occupation")
          });
          const bubbleTitle = document.createElement("title");
          bubbleTitle.textContent = String(row.title || "Occupation");
          circle.appendChild(bubbleTitle);
          const selectOccupation = function () { selected.index = item.index; draw(); };
          circle.addEventListener("click", selectOccupation);
          circle.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              selectOccupation();
            }
          });
          marks.appendChild(circle);
          if (showLabels || item.index === selected.index) {
            const label = String(row.title || "").replace(" and ", " & ");
            const text = make("text", { class: "bubble-label", x: x(exposure) + 9, y: y(outcome) + 4 }, label);
            labels.appendChild(text);
          }
        });
        yAxisTitle.textContent = currentMetric.axis;
        const selectedRow = rows[selected.index] || {};
        setText("detail-title", selectedRow.title || "Select an occupation");
        const socCodes = Array.isArray(selectedRow.soc_2018_codes) ? selectedRow.soc_2018_codes : String(selectedRow.soc_2018_code || "").split(";").filter(Boolean);
        setText("detail-code", selectedRow.onet_soc_code || "O*NET unavailable");
        const mappingFlags = String(selectedRow.data_quality_flags || "").split(";").filter(Boolean);
        const mappingWarnings = [];
        if (mappingFlags.includes("uniform_crosswalk_fallback")) mappingWarnings.push("Uniform crosswalk fallback; no source allocation was available.");
        if (mappingFlags.includes("shared_soc_crosswalk")) mappingWarnings.push("Shared SOC target; top-line SOC weighting deduplicates this target.");
        if (mappingFlags.includes("missing_crosswalk")) mappingWarnings.push("No SOC mapping is available; SOC-linked market fields are not available.");
        const mappingWarning = mappingWarnings.length ? " " + mappingWarnings.join(" ") : "";
        setText("detail-mapping", (socCodes.length > 1 ? "Reference metrics weighted across " + socCodes.length + " SOC mappings: " + socCodes.join(", ") + "." : "SOC mapping: " + (socCodes[0] || "not available") + ".") + mappingWarning);
        setText("detail-exposure", numeric(selectedRow.ai_exposure) == null ? "Not available" : numeric(selectedRow.ai_exposure).toFixed(2));
        setText("detail-outcome-label", currentMetric.label);
        setText("detail-outcome", currentMetric.format(numeric(selectedRow[currentMetric.field])));
        setText("detail-employment", workers(numeric(selectedRow.employment_2024)));
        setText("detail-growth", percent(numeric(selectedRow.employment_change_2024_2034_pct)));
        setText("detail-interpretation", selectedRow.title ? currentMetric.note : "Select an occupation to see a plain-language interpretation.");
        renderTasks(selectedRow);
        renderWorkerReviews(selectedRow);
        deepReviewButton.disabled = !llmEnabled || !selectedRow.title;
        deepReviewResult.hidden = true;
        deepReviewSummary.textContent = "";
        deepReviewEvidence.innerHTML = "";
      }
      metricSelect.addEventListener("change", draw);
      search.addEventListener("input", draw);
      taskFilter.addEventListener("input", function () { renderTasks(rows[selected.index]); });
      taskTypeFilter.addEventListener("change", function () { renderTasks(rows[selected.index]); });
      workerReviewSourceFilter.addEventListener("change", function () { renderWorkerReviews(rows[selected.index]); });
      workerReviewTopicFilter.addEventListener("change", function () { renderWorkerReviews(rows[selected.index]); });
      rows.slice().sort(function (left, right) { return String(left.title || "").localeCompare(String(right.title || "")); }).forEach(function (row) {
        const option = document.createElement("option"); option.value = row.onet_soc_code || ""; option.textContent = row.title || row.onet_soc_code || "Occupation"; bridgeSelect.appendChild(option);
      });
      const defaultBridge = payload.bridge || null;
      if (defaultBridge && defaultBridge.source && defaultBridge.source.onet_soc_code) bridgeSelect.value = defaultBridge.source.onet_soc_code;
      bridgeSelect.addEventListener("change", function () { loadBridge(bridgeSelect.value); });
      deepReviewButton.addEventListener("click", deepReview);
      reset.addEventListener("click", function () { search.value = ""; taskFilter.value = ""; taskTypeFilter.value = "all"; metricSelect.value = "wage"; selected.index = 0; draw(); });
      if (llmEnabled) deepReviewStatus.textContent = "Optional review sends the selected occupation and mapping to the configured endpoint. Use only an endpoint you trust.";
      updateKpis(); draw(); renderBridge(defaultBridge);
    }());
  </script>
</body>
</html>
"""


def render(
    rows: list[dict[str, str]],
    summary: dict[str, object],
    groups: list[dict[str, object]],
    tasks: list[dict[str, str]] | None = None,
    bridge: dict[str, object] | None = None,
    reviews: list[dict[str, object]] | None = None,
) -> str:
    del groups
    display_rows = aggregate_onet_rows(rows)
    tasks_by_onet: dict[str, list[dict[str, str]]] = {}
    for task in tasks or []:
        tasks_by_onet.setdefault(task.get("onet_soc_code", ""), []).append(task)
    reviews_by_onet = {}
    if reviews:
        from .reviews import summarize_reviews

        for row in display_rows:
            code = row.get("onet_soc_code", "")
            if code:
                reviews_by_onet[code] = summarize_reviews(reviews, code)
    dataset_notice = (
        "DEMO DATASET — values are synthetic examples for interface testing; do not use for labor-market decisions."
        if any(str(row.get("data_quality_flags", "")).casefold() == "demo_data" for row in display_rows)
        else ""
    )
    if not dataset_notice:
        provenance_fields = (
            "onet_version",
            "wage_vintage",
            "projection_vintage",
            "crosswalk_method",
            "ai_exposure_source",
        )
        if any(
            not all(str(row.get(field, "")).strip() for field in provenance_fields)
            for row in display_rows
        ):
            dataset_notice = (
                "DATA QUALITY NOTICE — provenance is incomplete for one or more records; "
                "validate source versions before using these values."
            )
    payload = json.dumps(
        {
            "rows": display_rows,
            "summary": summary,
            "tasks_by_onet": tasks_by_onet,
            "reviews_by_onet": reviews_by_onet,
            "bridge": bridge,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")
    return (
        HTML_TEMPLATE.replace("__ATLAS_DATA__", payload)
        .replace("__LLM_ENABLED__", json.dumps(LLM_REVIEW_CLIENT.config.enabled))
        .replace("__DATASET_NOTICE__", dataset_notice)
    )


def write_site(
    site_dir: Path,
    rows: list[dict[str, str]],
    summary: dict[str, object],
    groups: list[dict[str, object]],
    tasks: list[dict[str, str]] | None = None,
    bridge: dict[str, object] | None = None,
    reviews: list[dict[str, object]] | None = None,
) -> Path:
    site_dir.mkdir(parents=True, exist_ok=True)
    index = site_dir / "index.html"
    index.write_text(render(rows, summary, groups, tasks, bridge, reviews), encoding="utf-8")
    return index
