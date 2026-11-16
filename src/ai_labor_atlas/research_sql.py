"""Small portable analytical warehouse; source units never share an unlabeled value."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .comparison import load_snapshot
from .intelligence import load_market
from .io import read_csv
from .resources import resource_path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE source(source_id TEXT PRIMARY KEY, construct TEXT NOT NULL, period TEXT NOT NULL, unit TEXT NOT NULL, source_url TEXT NOT NULL);
CREATE TABLE occupation(soc TEXT PRIMARY KEY, title TEXT NOT NULL);
CREATE TABLE metric(soc TEXT REFERENCES occupation, source_id TEXT REFERENCES source,
 value REAL NOT NULL CHECK(value>=0), PRIMARY KEY(soc,source_id));
CREATE TABLE task(task_text TEXT PRIMARY KEY);
CREATE TABLE task_usage(task_text TEXT REFERENCES task, source_share_pct REAL NOT NULL CHECK(source_share_pct>=0),
 PRIMARY KEY(task_text));
CREATE TABLE occupation_task(soc TEXT REFERENCES occupation, task_text TEXT REFERENCES task,
 allocation_weight REAL NOT NULL CHECK(allocation_weight>0 AND allocation_weight<=1),
 PRIMARY KEY(soc,task_text));
CREATE TABLE market_observation(source_id TEXT REFERENCES source, period TEXT NOT NULL, industry TEXT NOT NULL,
 metric TEXT NOT NULL, value REAL, unit TEXT NOT NULL, retrieved_at TEXT NOT NULL,
 source_vintage TEXT NOT NULL, seasonal_adjustment TEXT NOT NULL, PRIMARY KEY(source_id,period));
CREATE INDEX task_soc_idx ON occupation_task(soc);
"""

QUERIES = {
    "task_mass_conservation": """SELECT SUM(u.source_share_pct) AS source_matched_pct,
        SUM(u.source_share_pct*w.weight_sum) AS allocated_pct
        FROM task_usage u JOIN (SELECT task_text,SUM(allocation_weight) AS weight_sum
        FROM occupation_task GROUP BY task_text) w USING(task_text)""",
    "largest_rank_gaps": """WITH paired AS (
        SELECT o.soc,o.title, MAX(CASE WHEN source_id='microsoft' THEN value END) AS applicability,
        MAX(CASE WHEN source_id='anthropic' THEN value END) AS usage_pct
        FROM occupation o JOIN metric m USING(soc) GROUP BY o.soc,o.title HAVING COUNT(*)=2), ranked AS (
        SELECT *,100.0*(RANK() OVER(ORDER BY applicability)-1+(COUNT(*) OVER(PARTITION BY applicability)-1)/2.0)/(COUNT(*) OVER()-1) AS applicability_rank,
        100.0*(RANK() OVER(ORDER BY usage_pct)-1+(COUNT(*) OVER(PARTITION BY usage_pct)-1)/2.0)/(COUNT(*) OVER()-1) AS usage_rank
        FROM paired)
        SELECT *,usage_rank-applicability_rank AS gap_pp FROM ranked ORDER BY ABS(gap_pp) DESC,soc LIMIT 12""",
    "monthly_market_change": """WITH endpoints AS (
        SELECT source_id,MIN(period) AS first,MAX(period) AS last FROM market_observation WHERE value IS NOT NULL GROUP BY source_id)
        SELECT a.source_id,a.industry,a.metric,a.unit,a.period AS first,b.period AS last,
        100.0*(b.value-a.value)/NULLIF(a.value,0) AS change_pct
        FROM endpoints e JOIN market_observation a ON a.source_id=e.source_id AND a.period=e.first
        JOIN market_observation b ON b.source_id=e.source_id AND b.period=e.last""",
}


def build_warehouse(path: Path) -> dict:
    if path.exists():
        # This generated database is replaced transactionally by a fresh adjacent file.
        temp = path.with_name(path.name + ".building")
    else:
        temp = path
    path.parent.mkdir(parents=True, exist_ok=True)
    if temp.exists():
        temp.unlink()
    snapshot = load_snapshot()
    connection = sqlite3.connect(temp)
    try:
        connection.executescript(SCHEMA)
        connection.executemany(
            "INSERT INTO source VALUES(?,?,?,?,?)",
            [
                (
                    "microsoft",
                    "consumer Copilot task applicability",
                    "2024-01-01/2024-09-30",
                    "score_0_1",
                    "https://github.com/microsoft/working-with-ai",
                ),
                (
                    "anthropic",
                    "fractionally allocated released Claude task conversations",
                    "release_2025-02-10; CSV observation dates unspecified",
                    "percent_of_released_conversations",
                    "https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/release_2025_02_10",
                ),
            ],
        )
        for row in snapshot["source_occupations"]:
            connection.execute(
                "INSERT INTO occupation VALUES(?,?)", (row["soc"], row["title"])
            )
            for source, key in [
                ("microsoft", "ms_applicability"),
                ("anthropic", "claude_share_pct"),
            ]:
                if row.get(key) is not None:
                    connection.execute(
                        "INSERT INTO metric VALUES(?,?,?)",
                        (row["soc"], source, row[key]),
                    )
        tasks = read_csv(resource_path("task_usage_links.csv"))
        for row in tasks:
            connection.execute("INSERT OR IGNORE INTO task VALUES(?)", (row["task"],))
            connection.execute(
                "INSERT OR IGNORE INTO task_usage VALUES(?,?)",
                (row["task"], float(row["source_share_pct"])),
            )
            connection.execute(
                "INSERT INTO occupation_task VALUES(?,?,?)",
                (row["soc"], row["task"], 1 / int(row["soc_count"])),
            )
        for row in load_market(resource_path("market_observations.csv").parent):
            connection.execute(
                "INSERT OR IGNORE INTO source VALUES(?,?,?,?,?)",
                (
                    row["source_id"],
                    row["metric"],
                    "monthly; dates in observations",
                    row["unit"],
                    row["source_url"],
                ),
            )
            connection.execute(
                "INSERT INTO market_observation VALUES(?,?,?,?,?,?,?,?,?)",
                tuple(
                    row[k]
                    for k in (
                        "source_id",
                        "period",
                        "industry",
                        "metric",
                        "value",
                        "unit",
                        "retrieved_at",
                        "source_vintage",
                        "seasonal_adjustment",
                    )
                ),
            )
        connection.commit()
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Warehouse foreign keys failed")
        connection.row_factory = sqlite3.Row
        results = {
            key: [dict(r) for r in connection.execute(query)]
            for key, query in QUERIES.items()
        }
    finally:
        connection.close()
    if temp != path:
        temp.replace(path)
    return results
