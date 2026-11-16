-- task_mass_conservation
SELECT SUM(u.source_share_pct) AS source_matched_pct,
        SUM(u.source_share_pct*w.weight_sum) AS allocated_pct
        FROM task_usage u JOIN (SELECT task_text,SUM(allocation_weight) AS weight_sum
        FROM occupation_task GROUP BY task_text) w USING(task_text);

-- largest_rank_gaps
WITH paired AS (
        SELECT o.soc,o.title, MAX(CASE WHEN source_id='microsoft' THEN value END) AS applicability,
        MAX(CASE WHEN source_id='anthropic' THEN value END) AS usage_pct
        FROM occupation o JOIN metric m USING(soc) GROUP BY o.soc,o.title HAVING COUNT(*)=2), ranked AS (
        SELECT *,100.0*(RANK() OVER(ORDER BY applicability)-1+(COUNT(*) OVER(PARTITION BY applicability)-1)/2.0)/(COUNT(*) OVER()-1) AS applicability_rank,
        100.0*(RANK() OVER(ORDER BY usage_pct)-1+(COUNT(*) OVER(PARTITION BY usage_pct)-1)/2.0)/(COUNT(*) OVER()-1) AS usage_rank
        FROM paired)
        SELECT *,usage_rank-applicability_rank AS gap_pp FROM ranked ORDER BY ABS(gap_pp) DESC,soc LIMIT 12;

-- monthly_market_change
WITH endpoints AS (
        SELECT source_id,MIN(period) AS first,MAX(period) AS last FROM market_observation WHERE value IS NOT NULL GROUP BY source_id)
        SELECT a.source_id,a.industry,a.metric,a.unit,a.period AS first,b.period AS last,
        100.0*(b.value-a.value)/NULLIF(a.value,0) AS change_pct
        FROM endpoints e JOIN market_observation a ON a.source_id=e.source_id AND a.period=e.first
        JOIN market_observation b ON b.source_id=e.source_id AND b.period=e.last;