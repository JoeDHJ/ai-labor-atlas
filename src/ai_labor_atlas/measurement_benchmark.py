"""Transparent task-text benchmark against published classifier labels (silver labels)."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from .io import read_csv, write_csv, write_json
from .pipeline import _read_tsv


def tokens(text):
    return re.findall(r"[a-z]{2,}", text.casefold())


def scores(actual, predicted):
    tp = sum(a and p for a, p in zip(actual, predicted))
    tn = sum(not a and not p for a, p in zip(actual, predicted))
    fp = sum(not a and p for a, p in zip(actual, predicted))
    fn = sum(a and not p for a, p in zip(actual, predicted))
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    specificity = tn / (tn + fp) if tn + fp else 0
    return {
        "n": len(actual),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": (tp + tn) / len(actual) if actual else None,
        "balanced_accuracy": (recall + specificity) / 2,
        "physical_precision": precision,
        "physical_recall": recall,
        "physical_f1": 2 * precision * recall / (precision + recall)
        if precision + recall
        else 0,
    }


def reconstruct_applicability(raw: Path) -> dict:
    """Independent implementation of the published weighted score equation."""
    iw = {r["IWA"]: r for r in read_csv(raw / "microsoft_iwa.csv")}
    weights = {r["SOC Code"]: r for r in read_csv(raw / "microsoft_weights.csv")}
    np = {r["SOC Code"]: r for r in read_csv(raw / "microsoft_nonphysical_weights.csv")}
    linked = {}
    for row in read_csv(raw / "microsoft_soc_iwas.csv"):
        linked.setdefault(row["SOC Code"], set()).add(row["IWA"])
    errors = []
    for row in read_csv(raw / "microsoft_scores.csv"):
        soc = row["SOC Code"]
        total = sum(float(weights[soc][iwa]) for iwa in sorted(linked[soc]))
        score = 0
        for iwa in sorted(linked[soc]):
            m = iw[iwa]
            for side, w in [("user", weights), ("ai", np)]:
                if float(m["share_" + side]) > 0.0005:
                    score += (
                        0.5
                        * float(w[soc][iwa])
                        / total
                        * float(m["completion_" + side])
                        * float(m["impact_scope_" + side])
                    )
        errors.append(abs(score - float(row["ai_applicability_score"])))
    maximum = max(errors)
    if maximum > 1e-10:
        raise ValueError(f"Published score reconstruction differs: {maximum}")
    return {
        "soc_count": len(errors),
        "maximum_absolute_error": maximum,
        "tolerance": 1e-10,
        "passed": True,
        "interpretation": "Verifies implementation of the published equation, not construct validity.",
    }


def build_benchmark(raw: Path, target: Path) -> dict:
    labels = {
        r["Task ID"]: r["Physical"] == "True"
        for r in read_csv(raw / "microsoft_physical.csv")
    }
    texts = {}
    for row in _read_tsv(raw / "benchmark_tasks_29_0.txt"):
        task_id = row["Task ID"]
        if task_id in texts and texts[task_id] != row["Task"]:
            raise ValueError("Conflicting text for one source task ID")
        texts[task_id] = row["Task"]
    train, test = [], []
    # Keep identical normalized wording together to prevent exact text leakage.
    groups = {}
    for task_id, text in texts.items():
        if task_id in labels:
            groups.setdefault(" ".join(text.casefold().split()), []).append(task_id)
    grouped = [[], []]
    for ids in groups.values():
        group_label = int(sum(labels[k] for k in ids) > len(ids) / 2)
        grouped[group_label].append(ids)
    for label in (False, True):
        matched = sorted(grouped[int(label)], key=lambda ids: min(map(int, ids)))
        for index, ids in enumerate(matched):
            (test if index % 5 == 0 else train).extend(ids)
    counts, docs = [Counter(), Counter()], [0, 0]
    for task_id in train:
        label = int(labels[task_id])
        counts[label].update(tokens(texts[task_id]))
        docs[label] += 1
    vocabulary = {t for t in counts[0] + counts[1] if counts[0][t] + counts[1][t] >= 3}
    totals = [sum(v for t, v in c.items() if t in vocabulary) for c in counts]

    def predict(text):
        features = Counter(t for t in tokens(text) if t in vocabulary)
        logp = [
            math.log(docs[c] / len(train))
            + sum(
                n * math.log((counts[c][t] + 1) / (totals[c] + len(vocabulary)))
                for t, n in features.items()
            )
            for c in (0, 1)
        ]
        return logp[1] > logp[0]

    physical_words = {
        "repair",
        "install",
        "operate",
        "lift",
        "clean",
        "assemble",
        "weld",
        "drive",
        "feed",
        "load",
        "unload",
        "cut",
        "move",
    }
    majority = docs[1] > docs[0]
    actual = [labels[k] for k in test]
    predictions = [predict(texts[k]) for k in test]
    keyword = [bool(set(tokens(texts[k])) & physical_words) for k in test]
    errors = [
        {
            "task_id": k,
            "task": texts[k],
            "published_physical": labels[k],
            "predicted_physical": p,
            "human_review": "pending",
        }
        for k, p in zip(test, predictions)
        if p != labels[k]
    ]
    result = {
        "label_status": "Published Microsoft LLM classifier labels; no independent human gold labels",
        "scope": "Physical versus nonphysical task text; not AI exposure or job replacement",
        "split": "Group identical case/whitespace-normalized task text, stratify by group-majority silver label, order groups by smallest numeric task ID; every fifth group held out",
        "train_count": len(train),
        "test_count": len(test),
        "vocabulary_size": len(vocabulary),
        "matched_task_ids": len(train) + len(test),
        "source_label_count": len(labels),
        "source_text_count": len(texts),
        "task_text_source": "Official O*NET 29.0 Task Statements; matched by published task ID",
        "unique_text_groups": len(groups),
        "mixed_label_text_groups": sum(
            len({labels[k] for k in ids}) > 1 for ids in groups.values()
        ),
        "exact_text_overlap_train_test": len(
            {" ".join(texts[k].casefold().split()) for k in train}
            & {" ".join(texts[k].casefold().split()) for k in test}
        ),
        "train_physical_count": docs[1],
        "test_physical_count": sum(actual),
        "majority": scores(actual, [majority] * len(test)),
        "keyword_rule": scores(actual, keyword),
        "multinomial_nb": scores(actual, predictions),
        "review_queue": errors[:40],
        "score_reconstruction": reconstruct_applicability(raw),
        "limitations": "Systematic text-group holdout is not a random labor-market sample; related wording can cross groups. Task IDs may have text revisions between source releases. Agreement with silver labels is not verified human accuracy. No tuning uses held-out outcomes.",
    }
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / "measurement_benchmark.json", result)
    write_csv(
        target / "task_review_queue.csv",
        errors[:40],
        ["task_id", "task", "published_physical", "predicted_physical", "human_review"],
    )
    return result
